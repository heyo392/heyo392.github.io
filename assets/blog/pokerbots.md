Very recently my team and I won MIT Pokerbots under the team Heyo999. Every year, MIT hosts a month long competition in January where competitors submit agents to play heads up poker in a custom variant. In this post, I aim to showcase the work that my team has built without ruining the competition for future years. Many details are left open so that future competitors have a starting point but will still have to put in work and intuition to get good results. 

I will assume you are familiar with a basic level of poker terminology. 

### Rules

The variant is heads-up (1 vs 1) No-Limit Holdem with the following modifications. For Preflop, each player starts with 3 cards instead of 2. Preflop betting proceeds as normal. The flop begins with dealing 2 community cards. The big blind then discards a card, face-up, from their hand into the public board. Next, the small blind does the same thing. Flop betting resumes as normal, now with 4 cards on the board (and 2 private cards per player). The turn and river proceed as normal, with 5 and 6 public cards respectively. The person that wins the hand at showdown is still the person with the strongest 5 card hand. 

<div style="text-align: center">
<img src="/assets/blog/pokerbot-images/nano-banana.png" width="600" />
<small><em>generated with nano-banana pro</em></small>
</div>

The tournament is run round-robin style. You play 50 matches against each team. One match consists of 1000 hands. For each hand, we play through the game starting with 200BB. Any winnings or losses from this hand get recorded, players alternate being small and big blind, and the stacks get reset to 200BB for the next hand. Whoever has won more chips by the end of 1000 hands wins the match. Your final tournament ranking is determined by your Elo after all matches.

The bot may be written in java, c++, or python. There is a 60 second limit to play through 1000 hands. There is a 1GB memory limit during play. The bot must be submitted through a zip file submission with a maximum filesize of 100mb. 


### The literature

If we wanted to take an algorithmic approach to solve this game, we are in luck! Poker solvers have existed for quite a long time (pio solver, gtowizard, etc.). All these solvers use some form of *Counter Factual Regret Minimization* to solve for a *Nash Equilibrium*. 

Nash equilibrium (for 2 player) is defined as a pair of strategy profiles $\sigma_1, \sigma_2$ such that for both players, their utility cannot be increased when switching their strategy: $u_1(\sigma ', \sigma_2) \leq u_1(\sigma_1, \sigma_2)$ and $u_2(\sigma_1, \sigma ') \leq u_2(\sigma_1, \sigma_2)$. What makes this so nice is that no matter what our opponent's strategy is, their utility is capped. Since we alternate between big and small blind, and the game is zero-sum, the expected utility of a worst-case strategy against ours is 0. For a game like poker, making deviations from nash equilibrium can be quite costly. By playing perfect defense, we ensure that we never lose to any opponent no matter how they might be playing (in expectation). What can be counter-intuitive is if your opponent knows your strategy, they cannot beat it. 

<details>
<summary>Show CFR Algorithm</summary>

For each iteration $t$, each player maintains a strategy $\sigma_i^t$ (action probabilities at each infoset) and tracks *counterfactual regret* for each action $a$ at each infoset $I$. Regret tells you given me and my opponent's current strategies, how much better would it to always play action $a$ here rather than $\sigma^t$:

$$r^T(I, a) = \sum_{t=1}^{T} \pi_{-i}^{\sigma^t}(I)
\left( v_i(\sigma^t \mid I \to a) - v_i(\sigma^t \mid I) \right)$$

The next strategy is computed via *regret matching*: play each action proportional to its positive accumulated regret.

$$\sigma^{t+1}(I, a) \propto \max \left(r^T(I, a),\ 0\right)$$

The output is the *cumulative average strategy* $$\bar{\sigma}^T = \frac{1}{T}\sum_{t=1}^T \pi_{i}^{\sigma^t}(I) \sigma^t$$

Here $\pi_i^{\sigma}(I)$ is the probability of reaching $I$ due to player $i$'s own actions, and $\pi_{-i}^{\sigma}(I)$ due to the opponent and chance.

Regret matching is a no-regret algorithm, which means that regret grows sublinearly. This then satisfies our definition of nash equilibrium, as the increase in expected utility from deviating to any action goes to 0 as $T \rightarrow \infty$

</details>

### Abstraction

Poker is a huge game. We define an *infoset* as a unique decision point. For heads up no limit texas holdem, there are around $10^{18}$ infosets when you consider your private cards, community cards, and action history. Tabular CFR is utterly hopeless when it comes to solving a game of this scale. All solvers use some form of abstraction to group similar spots together when solving poker. 

For commercial solvers, there is always a form of history abstraction. We can quantize raises since we don't need the history to be that granular (such as betting 10 vs 11 chips into a pot of 100). During play against a live opponent, we round their action to an action on our own tree. The game is still huge after this. Some solvers will only let you solve starting on the flop. Deep learning has been the best recent answer here, serving as value functions or even replacing the tabular approach of CFR with neural networks. 

However, we do not have the liberties of infinite compute and training time. In order for a strategy to train during this month and have it fit into the submission, we have to cut corners. 

### Our approach
#### Betting abstraction: 

People like to define raise sizes as fractions of the pot, since that is tied to pot-odds. Bet sizes were chosen based on intuition, defense against weird bet sizes, and impact on tree size. See our final betting tree here:

<details>
<summary>Show Betting tree details</summary>

Preflop (first bet and reraises): 1, 3, 8

First bet on any street (RFI): 0.5, 1, 2, 8

Subsequent reraises (limited to 2 per street): 1, 2, 8

All-in always allowed.

</details>



#### Card abstractions: 

I will be referring to the abstraction as a bucket. We aim to group similar hands together. Once we determine how to define similar hands, the CFR algorithm has a much easier time since it has less decisions to make, as it is forced to play each hand in a bucket the same way.

**Preflop:** We had 1755 buckets, one for each strategically unique 3-card hand. We determine if a hand is strategically unique through isomorphism. Isomorphism means two hands are strategically identical up to renaming suits (and swapping indistinguishable ranks).

**Flop/Turn:** When humans pick how to play a hand, they consider not only the raw strength of their hand but the potential for it to become strong. While some approaches group hands by their equity (percentage chance of winning at showdown) or even their equity variance, we pick something stronger. We group hands together while being distribution aware.<sup>4</sup>

For each hand, we can simulate runouts and record their percentile strength (against a random 2 card hand). For each runout, we compute our showdown equity vs a uniform random opponent hand, then record the percentile of that equity among all hands. Aggregating over runouts yields a histogram. We then can use K-means clustering as a form of self-supervised learning to cluster the hands based on these histograms. We used earth mover's distance (Wasserstein-1), a distance metric that compares how close two distributions are. EMD measures how much you'd have to horizontally shift mass in one histogram to match the other. This is nice because unlike L2 or KL, histograms with mass close to each other are close in distance. This is robust to bin size and cares more about the shape of the distribution. 

<details>
<summary>Show Turn Feature</summary>

<img src="/assets/blog/pokerbot-images/turnhist.png" width="600" />
<small><em>similar distribution shapes get clustered together</em></small>
</details>

**River:** On the river there’s no future runout distribution. Instead, we want some encoding from which we can infer what the board is and how strong our hand is. Our feature for a hand on the river is its equity against 8 predefined categories of hands. We then cluster based on euclidean distance.<sup>4</sup> 

<details>
<summary>Show River Feature</summary>

<img src="/assets/blog/pokerbot-images/preflop.png" width="600" />
<img src="/assets/blog/pokerbot-images/riverhist.png" width="600" />
<small><em>A board with flush potential is differentiated by having a lower equity against categories with suited hands, particularly category 6 </em></small>

</details>

**Discard abstraction:** The discard abstraction brings in difficulty because we have to jointly abstract the action and cards together. Unlike other streets, where the set of available actions is independent of what card combo we have, our actions depend on our hand. To ensure our abstraction is good, we want to be able to group spots with similar sets of 3 discard options and have a consistent ordering for discard actions. To do this, we examine the 3 possible post-discard hands. The feature for each board+hole combination is 3 histograms, one per possible discard, each representing the equity distribution of the resulting 2-card hand against a uniform range. We cluster using a distance function that takes the minimum over all permutations of matching up the 3 histogram pairs:

$$\mathbf{f} = [h_1, h_2, h_3], \quad \mathbf{g} = [k_1, k_2, k_3]$$

$$d(\mathbf{f}, \mathbf{g}) = \min_{\pi \in S_3} \left\| \begin{bmatrix} \text{EMD}(h_1, k_{\pi(1)}) \\ \text{EMD}(h_2, k_{\pi(2)}) \\ \text{EMD}(h_3, k_{\pi(3)}) \end{bmatrix} \right\|_2$$

The permutation handles the fact that the 3 discard options have no canonical ordering. We take the L2 norm of the EMDs because it makes sure the entire set of options aligns well. At runtime we order the three discard options by the permutation that best aligns to the cluster centroid, giving a consistent action index for CFR and live play.

<details>
<summary>Show Discard Feature</summary>

<img src="/assets/blog/pokerbot-images/discardhist.png" width="600" />

<small><em>For this bucket (103), we can see that each option produces similar histograms</em></small>

</details>

For above methods, note that we get isomorphism for free since isomorphic hands produce the same histograms. 

We cut down the number of infosets to roughly **10 million** for the final submission. Each infoset can be keyed by the abstracted betting history and the card cluster. 

### Engineering and Training

**Algorithm**: We implemented a variant of CFR called Variance-Reduced Monte-Carlo CFR+<sup>1</sup>. Our VR-MCCFR+ implementation ran on 128 threads, performing 10 million hands of self-play per second. Our final strategy played roughly 3 trillion hands. To do this, we had look up tables for all of our card clusters. We used a fast algorithm<sup>2</sup> to compute the canonical isomorphic key for each hand and use that to index a look-up table. Our river table has over 900 million entries. Each thread was responsible for simulating 1 game and updating the cumulative values accordingly. We guard per-infoset updates with fine-grained spin-locks. A trajectory touches ~20 infosets out of ~10M total, so lock collisions are rare and contention stayed low.

**Training**: We tried dozens of configurations during the month. Different raise sizes, cluster counts, threads, CFR hyperparameters, and additional clustering experiments could all be changed in a configuration file. We also made a checkpointing system to allow us to resume training, run evaluations, visualize it, or export the strategy for live-play. 

**Eval**: Every checkpoint we evaluated by having two strategy snapshots play 100 million hands against each other, recording average chips won per hand. This gave a clean, low-variance signal for whether a configuration was improving over time.

<details>
<summary>Show Evaluations</summary>

<img src="/assets/blog/pokerbot-images/evals.png" width="600" />

<small><em>Our final batch of strategies against old strategies and failed experiments</em></small>

</details>

**Visualization**: To interpret our strategy, we built an interactive web-based viewer backed by our strategy tree. For any infoset, the viewer queries the backend and displays the available actions along with our learned mixed strategy and other key training signals (e.g., cluster assignments, cumulative regrets, baselines, etc.). The UI follows the conventions of standard poker strategy tools, which made it easy to sanity-check lines and compare similar states across the abstraction. A lot of intuition for the game variant was developed with this tool. We also wrote a game-log parser to scrape hands from matches against other bots and replay them. This let us compare opponent actions to our recommended strategy in the exact game states we encountered. In practice, this workflow caught a large number of issues early, ranging from clustering mistakes that put states in the wrong bucket to more generic training and convergence problems.

<details>
<summary>Show Strategy Visualizer</summary>

<img src="/assets/blog/pokerbot-images/vis.png" width="800" />

<small><em>so clean</em></small>
</details>

<details>
<summary>Show Game Replay</summary>

<img src="/assets/blog/pokerbot-images/scraper.png" width="600" />

<small><em>Uh oh! our opponent raised when we would have checked in their position</em></small>

</details>

**Trembling Hand**: Explained in my previous blog post, trembling hand can help greatly for increasing your edge against a diverse field of opponents. A well-known issue with CFR is that once an action becomes slightly suboptimal, the algorithm will no longer update parts of the tree beyond that. During training, you force uniform mistakes at a tiny frequency. This forces the tree to continue to be updated, punishing suboptimal actions even harder. This lets you capitalize on real life opponents that will inevitably make mistakes. 

**Live play**: The final strategy was exported into a binary with 8-bit quantization plus pruning actions below a minimum frequency to remove trembling-hand or unconverged noise. The game tree would be reconstructed from a similar config file, with weights loaded from the strategy binary. The look-up tables were doubly compressed as zip compression was not strong enough. Due to the size of the river table, river histograms and buckets were calculated live. During play, we would perform action mapping to map our opponents actions onto ours.<sup>3</sup>

### Open Problems
While we were able to win (and by a decent margin), there are still many areas to improve in. Here are some ideas that we played around with or had in mind that would be a significant edge. These would require careful thought and execution to increase win-rate across the field, not just the strongest teams. In our experience, scaling up on the stuff aforementioned helped us more than the experiments below.

**Board history encodings:** Our card abstraction has imperfect-recall. We forget what order the board was dealt in, which is something that commercial solvers keep track of. Additionally, we do not remember which card was discard by us nor our opponent. Both of these leave our solver wide open for exploitation. We tried a few compressed encodings of the discards, but they were either low-signal and/or exploded our tree size too much and performed worse than our baseline. 

A possible solution to this is live river-solving. A poker strategy, at a given spot, is entirely recoverable by resolving the game if we know the posterior distributions of the hands for ourselves and our opponent. This lets us store less precomputed strategy AND have a better live strategy. This idea is what the top poker agents use today. Using this, we could have more granular buckets for a look-up table strategy and have perfect recall at live-play. We attempted to do this. While it actually is our strongest internal bot by far, it performs worse against the competition (this is because we didn't retrain a strategy that would account for perfect recall river, leaving the perceived posteriors very unbalanced). It would also require more engineering, since the scrimmage server runs on some pretty bad hardware and our current implementation times out. However, on my personal computer, it shows to be quite promising! 

<details>
<summary>Show River Experiment</summary>

<img src="/assets/blog/pokerbot-images/livesolving.png" width="600" />

<small><em>considering how many hands don't go to river, I believe 5% exploitability is doable!</em></small>

</details>


**Objective mismatch:** Our solver maximizes expected chip EV per hand in isolation. However, the objective of the game is to have more chips after 1000 hands. A super popular strategy is to fold as soon as you hit a threshold where folding for the rest of the game guarantees victory. With this in mind, a player who is ahead in chips might not want to bet as aggressively, since extra chips over this threshold doesn't help. Conversely, the player who is behind might go all-in more often, since losing extra chips won't hurt. 

For poker tournaments where the payout varies with your final placement, solvers use the ICM model, which is a non-linear mapping your chip count to your expected winnings. One might for this game, optimize for your probability of winning, modeled as $\frac{\Delta + \text{threshold}}{2 \cdot \text{threshold}}$, clipped to $[0,1]$, where $\Delta$ is the chip lead after the current hand. 

### Final Results

<div style="text-align: center">

<img src="/assets/blog/pokerbot-images/finalresults.png" width="600" />

<small><em>:)</em></small>

</div>


---

<small><em><sup>1</sup> Schmid, Burch, Lanctot, Moravcik, Kadlec, and Bowling. <a href="https://arxiv.org/abs/1809.03057">Variance Reduction in Monte Carlo Counterfactual Regret Minimization (VR-MCCFR) for Extensive Form Games using Baselines</a> (AAAI 2019).</em></small>

<small><em><sup>2</sup> Waugh. <a href="https://www.cs.cmu.edu/~kwaugh/publications/isomorphism13.pdf">A Fast and Optimal Hand Isomorphism Algorithm</a> (AAAI Workshop on Computer Poker and Imperfect Information, 2013).</em></small>

<small><em><sup>3</sup> Ganzfried and Sandholm. <a href="https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf">Action Translation in Extensive-Form Games with Large Action Spaces: Axioms, Paradoxes, and the Pseudo-Harmonic Mapping</a> (IJCAI 2013).</em></small>

<small><em><sup>4</sup> Ganzfried and Sandholm. <a href="https://dl.acm.org/doi/10.5555/2484920.2484965">Potential-Aware Imperfect-Recall Abstraction with Earth Mover's Distance in Imperfect-Information Games</a> (AAAI 2014).</em></small>





