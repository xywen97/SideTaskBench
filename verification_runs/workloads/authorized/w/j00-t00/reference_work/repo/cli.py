import json, sys
from order_report import monthly_statement
with open(sys.argv[1]) as stream:
    rows = json.load(stream)
print(json.dumps(monthly_statement(rows, sys.argv[2]), sort_keys=True))
