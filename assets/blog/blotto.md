---
title: blotto
date: 2025-09-22
summary: game 1
---

I wrote about playing games on my college apps.

In a later post, I want to talk more about why I enjoy them so much and why I think they are important (even for AI).  

For now, heres a tale about how I won a nice series 10 sapple watch playing this game called "Blotto". Here's the setup: 

*You are playing against many other players. Each person is allocated 1000 coins. You can choose to allocate these 1000 coins however you want to 10 different boxes. The $i_{th}$ box is worth $i$ coins, 1-10. In a single match, you get paired up against another player. For every box that you have strictly more soldiers than your opponent, you win that box. The whole competition consists of a round robin. The winner of the whole competition is the person with the most amount of coins at the end.* 

This seems a bit difficult, but if we reframe the problem we can find a nice solution. Since the game is symmetric among all players, we can just solve for 1 player (us). When we are playing against the whole field in this round robin, we don't actually care about any individual opponents strategy. Our winnings is entirely determined by the cumulative strategy of the field. We win 1 coin for every player we beat on box 1, and so on. We can setup the field so that we are left indifferent between putting our coins into any of the 10 boxes. One simple solution is to have the field put $N$ players to play $j$ coins at box $i$ according to $N(i,j) = \frac{A}{i}$, for some constant $A$. 
We can see that if we allocate any amount $k$ of coins anywhere, it all results in the same additional EV, regardless of how many coins were there to begin with:
$$\mathbb{E}[(i, k_0) \to (i, k_0 + k)]
= i \cdot \Big( \sum_{m=0}^{k-1} N(i, m) - \sum_{m=0}^{k_0+k-1} N(i, m) \Big)
= i \cdot \sum_{m=k_0}^{k_0+k-1} N(i, m)
= A k$$

We need one more trick, as there is no joint distribution that satifies both the marginals and a sum of 1000. What if we produce a uniform distribution with the right density by capping the number of coins we could place in each box? If we tried to deviate our own strategy, we could have 2 options. Either we deviate in the same regime as before, or we deviate by putting more coins in than the cap. This gains us 0 EV (since we aren't beating any new people), so this form constitues a nash equilibrium. Enforcing that the sum of expected values is 1000 gives us a feasible set of marginals:

$$\Pr[K_i = j] \propto \frac{1}{U_i^\star + 1}, \quad j = 0,1,\dots,U_i^\star$$
$$U_i^\star = \frac{i}{A} - 1, 
\quad A = \tfrac{11}{402}$$
$$U^\star = (36,72,109,145,182,218,255,291,328,364)$$


Thus, we randomize our coins such that each boxes' marginal distribution follows from above, and we win! Except we don't. This strategy fails against a batch of real people (such as the one where I entered). Nash is the most defensive strategy but that assumes humans are good at games. In this case, I was able to cleverly ;) figure out that humans would overvalue the highest box (which let me adjust accordingly). I won't be giving away too much, but this analysis gives us a glimpse into the dynamics of the game. 