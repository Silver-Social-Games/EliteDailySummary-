# New Elite Player Assignment

This initiative assigns monthly New Elite player exports among Elite Agents
using exact quotas and balanced purchase value, then creates or extends the
formatted assignment workbook.

Run the generator from the repository root:

```bash
python new_elite_players_adding/generate_assignment.py --input "PATH/TO/VIP Potential.csv" --output "PATH/TO/New_Elite_Players.xlsx" --quota Coral=62 --quota Gabriel=84 --quota Lee=66 --quota Rachel=32
```

The `@new-elite-player-assignment` Skill owns the full workflow, input rules,
workbook format, and verification details.
