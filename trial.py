from stage_staircase import AdaptiveStaircase

staircase = AdaptiveStaircase(
    start_val=147.0,
    min_val=0.01,
    max_val=316.0,
    max_trials=30,
    target_reversals=6,
    combination_factor=1,
)

while not staircase.is_finished():
    response = staircase.get_arrow_key()
    is_reversal = staircase.update(response)

print(staircase.get_threshold())