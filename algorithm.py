from functools import reduce
from stats import calculate_percentage_stats

## PUBLIC FUNCTIONS

# Returns 1, 2, or 0 if a tie
def winner(team1, team2):
    def catWinner(tup):
        s1, s2 = tup
        return 1 if s1 > s2 else 2 if s2 > s1 else 0
    w1, w2 = 0, 0    
    for r in map(catWinner, zip(team1, team2)):
        if r == 1:
            w1 += 1
        elif r == 2:
            w2 += 1
    #print(w1, w2)
    return 1 if w1 > w2 else 2 if w2 > w1 else 0

def sum_team_total(all_team_rosters):
    # Takes in two players, and adds their categories together
    def player_sum_func(p1, p2):
        return ("", tuple([p1i + p2i for p1i, p2i in zip(p1[1], p2[1])]))
    
    # Takes in a roster and returns cumulative team score by categories
    # KEEP IN MIND: The last four categories are percentage stats
    # They need to be reduced into percentages
    def team_sum_func(roster):
        # This has been summed
        summed_roster = reduce(player_sum_func, roster)
        
        # Now we calculate total FG and FT percentage
        return calculate_percentage_stats(summed_roster)

    return {k: team_sum_func(v)[1] for k, v in all_team_rosters.items()}

def get_team(all_players, names):
    def get_player_stats(name):
        for player, stats in all_players:
            if name == player:
                return (player, stats)
    return list(filter(lambda x: x != None, map(get_player_stats, names)))

def simulate_matchups(matchups, team_scores):
    # result is 0 for win, 1 for tie, 2 for loss
    def increment(d, k, result):
        if k not in d:
            d[k] = [0, 0, 0]
        d[k][result] += 1

    game_records = {}
    
    # Play every matchup and store results
    for team1, team2 in matchups:
        # Calculate the game winner
        result = winner(team_scores[team1], team_scores[team2])
            
        # Calculate record indices based on result
        resInd1, resInd2 = 1, 1
        if result == 1:
            resInd1, resInd2 = 0, 2
        elif result == 2:
            resInd1, resInd2 = 2, 0

        # Update record dictionary
        increment(game_records, team1, resInd1)
        increment(game_records, team2, resInd2)

    return game_records