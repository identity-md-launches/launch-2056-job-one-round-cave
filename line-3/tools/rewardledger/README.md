# RewardLedger

RewardLedger makes a stable, unsigned CSV review copy from a complete allocation report. It keeps units and amounts as text, includes the source report SHA-256, rejects missing fields and duplicate contributor IDs, and never creates a recipient or payment instruction.

Run the self-contained demo from the repository root:

```sh
python3 -B line-3/tools/rewardledger/rewardledger.py line-3/tools/rewardledger/example.json --output /tmp/rewardledger-demo.csv
```

Tried here: exit 0, producing a two-row CSV with the expected source hash. The tool uses only Python's standard library. Import every CSV column as text in a spreadsheet to avoid rounding large integer units.
