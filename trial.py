from stage_staircase import AdaptiveStaircase

staircase = AdaptiveStaircase(
    start_val=147.0,
    min_val=0.01,
    max_val=316.0,
    max_trials=30,
    target_reversals=6,
    combination_factor=1,
)

staircase = AdaptiveStaircase(start_val=147.0, min_val=0.0100, max_val=316.0, max_trials=30, target_reversals=7 , combination_factor=0)
staircase.start_algorithm()