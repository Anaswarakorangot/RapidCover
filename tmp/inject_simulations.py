import os

target_file = r"c:\Users\Admin\Desktop\RapidCover\RapidCover\backend\app\api\admin.py"
with open(target_file, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "triggers = detect_and_save_triggers(simulation.zone_id, db)" in line:
        indent = line[:line.find("triggers")]
        new_lines.append(f"{indent}# Auto-process payouts for instant demo effect\n")
        new_lines.append(f"{indent}for t in triggers:\n")
        new_lines.append(f"{indent}    from app.services.claims_processor import process_trigger_event\n")
        new_lines.append(f"{indent}    process_trigger_event(t, db)\n")

with open(target_file, "w") as f:
    f.writelines(new_lines)

print("Injected auto-processing into simulations successfully.")
