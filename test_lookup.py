from pathlib import Path

from database.customer_lookup import CustomerLookup


lookup = CustomerLookup(
    Path("exports") / "ServiceTitanCustomersExport.xlsx"
)

customer = lookup.find("843598")

print()
print(customer)
print()