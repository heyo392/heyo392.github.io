Last semester, I took a graduate-level class on multi-agent learning. This class focused on game theory, a field that I find quite underrated. For this article, I'll assume that you have a basic understanding of what CFR does and what it is used for.

For the final project, we were tasked with submitting a strategy for 4-player Leduc Poker, but with a twist. There were two teams of two players, and the earnings of each team were combined across its members. Players were allowed to collude with their teammate, but they did not receive any information about their partner’s cards.

### Challenge

We consider the 4-player Team Leduc Hold'em game described in the project specification.

*The deck consists of six cards: $\{J, J, Q, Q, K, K\}.$ The game has two betting rounds with fixed raise sizes ( $2$ preflop, $4$ postflop) and at most two raises per round, with a $1$ ante. The allowed actions are check/call, fold, or raise. Players act sequentially in order $1 \rightarrow 2 \rightarrow 3 \rightarrow 4.$ Players 1 and 3 form Team 13, and players 2 and 4 form Team 24. The player with the highest card who has not folded wins the pot (split evenly on ties). Team utility is the sum of individual payoffs. Teammates cannot communicate during play and do not observe each other's private cards. However, they may coordinate beforehand using a shared random signal: $\sigma = \sum_{j=1}^{L} p_j \, \sigma^{(j)}$, where each $\sigma^{(j)}$ is a behavioral strategy profile and $p_j$ is the probability of signal $j$.*

Formally, this problem is known as Team Maxmin Correlated Equilibrium (TMECor). 

The strategies were evalulated based on two metrics. Head-to-head utility against other teams in the class and exploitability. Exploitability is defined as the maximum utility a perfect counter-strategy could achieve against your strategy. At equilibrium, exploitability equals the value of the game. For this specific game, the exploitability of a uniform strategy is 6.1165.

### Toy Game
To gain intuition for this problem, consider the following toy game:

*Player 1 and 3 are on a team and player 2 is by themselves. Player 1 gets privately dealt either J, Q, K. Player 1 may either publically state that they have J, Q, or K. Player 2 then guesses Player 1's card. Finally, Player 3 guesses Player 1's card. Team 13 wins iff player 3 guesses it correctly but player 2 doesn't.*

In game theory, the most talked about equilbrium is the Nash equilibrium, where all actions are taken independently. This idea can extend to correlated actions. Correlated actions also have their own equilibrium. For example, two cars at a traffic stop will act on by their correlated equilibrium (with the traffic light providing the shared signal).

For humans, the optimal solution for the toy game is quite intuitive. We just need to map the shared signal to either 0, 1, or 2, and have Player 1 publically state their private card + shared signal modulo 3. Since Player 3 knows the shared signal, they always know Player 1's card. Since Player 2 does not know the shared signal, their posterior belief on Player 1's card is uniform so they guess at random. Hence, team13 has a 2/3 chance of winning. 

This demonstrates the power of correlation. Without correlation, the best that team13 could do is have Player 1 mix uniformly between announcing their private card and private card + 1 modulo 3. With a perfectly exploiting Player 2, their winrate is 1/2. 

Note: CFR would fail to even reach this strategy! With uniform initialization, no regrets ever accumulate because all actions are symmetric. Without perfect recall, regret signals collapse and the correlated structure is never discovered.

### TB-DAG
We turn to the Team Belief-DAG<sup>1</sup> to solve all of our problems. Intuitively what this does is enumerate all possible combinations of actions at public belief states. Our dag consists of nodes of public belief (say check-check-bet) and prescriptions (say {[if Team Member 1 has A do X, otherwise do Y], [If Team Member 1 has A do Y, otherwise do Y]...}). You can find the details for this in the paper.

<details>
<summary>Show TBDAG construction example</summary>

<img src="./assets/blog/team-leduc-images/tbdagexample.png" width="600" />

</details>

Since many many cartesian products are taken when building this dag, the size of this game is astronomical. The number of infosets in the base game is 12,000 per player, while the TBDAG has 2 million per team. Crucially, the terminal nodes and utilites are the same. We can now run CFR!

Usually a game tree represents both players on a single tree, while this has 2 separate DAGs. On each DAG, opponent actions show up as inactive nodes. We enumerate all inactive node branches and weight each terminal utility by chance probability × opponent reach (precomputed from the other team's DAG). This turns each DAG traversal into a single-player decision problem. Since we have two separate DAGs whose inactive node probabilities depend on each other's strategies, we alternate regret matching iterations between the two. Update one team's strategy, recompute the other team's terminal reach probabilities, and repeat. The output of the solver is the Nash equilibrium strategy profile for both teams on the TBDAG (probability of each prescription at each public belief).

<details>
<summary>Show Exploitability convergence</summary>

<img src="./assets/blog/team-leduc-images/dcfrexploitaability.png" width="600" />

</details>

From our first implementation, we optimized the solver (and switched to DCFR) to run in weeks all the way down to 20 minutes! 

### Sim2Real

To get 1 pure behavioral strategy out of this TBDAG, we simply follow one back from the root of the TBDAG to the terminals. When its our opponents turn to act, we enumerate all branches and when its our turn to act, we pick one prescription. Each prescription will tell us what action the player (either member 1 or 2) picks at each infoset the node represents. The weight of this strategy is equal to the probability of this path. 

<details>
<summary>Show Strategy Extraction</summary>

<img src="./assets/blog/team-leduc-images/mcsampling.png" width="600" />

</details>

While we have a (near) perfect solution for the game now, the submission format required 100 behavioral (independent) strategies and the probability of selecting each strategy. This is a huge compression as the number of behavioral strategies required to behave identically the TB-DAG is equal to the number of paths, which is exponential in depth. Here are the methods we came up with to preserve the strategy:

**Empirical Sampling**. 
We can naively sample paths from the root to terminals on the TBDAG using its branching probabilities, where each path corresponds to one pure strategy. This is very noisy given the size of the DAG. Instead, we greedily pick the edge that has been most underrepresented by previous paths.

**Combining Trees**. 
Two pure strategies that reach disjoint infosets can be merged into a single tree. This lets us effectively pack more pure strategies into our 100-tree budget, since one tree can encode multiple non-overlapping strategies.

<details>
<summary>Show Tree combining</summary>

<img src="./assets/blog/team-leduc-images/combiningtrees.png" width="600" />

</details>

**Weighting behavioral strategies**.

Previously, we would sample trees and weigh them evenly. We can do better. We constructed a new game where one team is restricted to playing from their 100 sampled strategies while the other team plays freely, then ran CFR to solve for optimal meta-weights. We then dropped near-zero-weight strategies, resampled new ones, and repeated. Iterating this process and keeping the best round gave us a nice exploitability improvement. 

The key insight here is that your exploitability is determined by the best counter-strategy. Without going into much detail, there always exists a best counter-strategy that is pure. Even though our strategy is restricted to 100 trees, the best counter-strategy can be represented on a single pure tree. This is why we run a restricted player against a TBDAG player. With this in mind, our new mini-game actually minimizes the original metric (while the above two tried to preserve probabilities). Thats what made this so effective. Since exploitability is a highly non-linear function, running another layer of CFR is the best way to minimize it.  

<details>
<summary>Show Meta-weight Finetuning</summary>

<img src="./assets/blog/team-leduc-images/finetuning.png" width="600" />

</details>

**Trembling Hand**.
Our final improvement aimed at increasing our profit against the other teams participating in the competition. While we aimed to play at nash equilibrium, there are actually an infinite number of them! All thats required is that supported actions have the same utility, and all unsupported actions do not exceed that. For example, if our opponent calls for 0.99 EV and folds for 1 EV, a strategy of [0, 1] would be nash equilibrium. However, we could modify our strategy in the call branch so that our opponent EVs become -1EV and 1EV. Since our opponent never calls at equilibrium, nothing changes. However, against a field where opponent makes mistakes, the 2nd strategy is much better for us. CFR struggles with this since it will stop updating parts of the tree once the EV becomes even marginally worse than other branches. This can leave "unused" parts of the tree "unconverged". 

We introduced an epsilon-uniform strategy during training, essentially forcing uniform "mistakes" at epsilon probability. By keeping every action alive with small probability, we ensure regret signals continue to propagate everywhere. We anneal $\varepsilon \to 0$ over time so that the final strategy approaches equilibrium while retaining better-trained off-equilibrium branches.<sup>2</sup> This also helped with compression a tiny bit (but not after meta-weight tuning).

### Conclusion

<details>
<summary>Show Exploitability Results</summary>

<img src="./assets/blog/team-leduc-images/finalexploitabilities.png" width="90%" />

</details>


<details>
<summary>Show Performance agains Class </summary>

<img src="./assets/blog/team-leduc-images/finalperformance.png" width="90%" />

</details>


I got two main takeaways:

The compression schemes stray from our intuition of what makes a good strategy. Greedily picking the highest probability paths will leave you highly exploitable. There is no such "best action" as each action with non-zero probability results in the same utility. 

We got a glimpse at how complicated optimal strategies can be. Back when poker solvers were first being invented, there was a paradigm shift. Overbetting used to be considered rude (or even banned) since the poker community believed it was bad. Multi-agent collaborative settings appear all around us and we have much to learn.

---

<small><em><sup>1</sup> Zhang, Farina, and Sandholm. <a href="https://arxiv.org/abs/2202.00789">Team Belief DAG</a> (ICML 2023).</em></small>

<small><em><sup>2</sup> This was also huge for us for the 2026 pokerbots competition 🤫🤫🤫.</em></small>