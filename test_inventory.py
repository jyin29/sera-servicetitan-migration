from sera.media_inventory import MediaInventory

inventory = MediaInventory("sera_media")

customers = inventory.load()

print("=" * 60)
print(f"Customers found: {len(customers)}")
print("=" * 60)

for customer in customers:

    print(f"\nLegacy Customer: {customer['legacy_id']}")

    for job in customer["jobs"]:

        print(f"   Job: {job['job_number']}")

        for file in job["files"]:

            print(f"      {file.name}")