import os

target_file = r"c:\Users\Admin\Desktop\RapidCover\RapidCover\backend\app\api\admin.py"
with open(target_file, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "triggers = detect_and_save_triggers(simulation.zone_id, db)" in line:
        indent = line[:line.find("triggers")]
        # CLEANUP: End all active triggers in the zone first to allow the new one to fire
        new_lines.append(f"{indent}from app.models.trigger_event import TriggerEvent\n")
        new_lines.append(f"{indent}from datetime import datetime\n")
        new_lines.append(f"{indent}db.query(TriggerEvent).filter(\n")
        new_lines.append(f"{indent}    TriggerEvent.zone_id == simulation.zone_id,\n")
        new_lines.append(f"{indent}    TriggerEvent.ended_at.is_(None)\n")
        new_lines.append(f"{indent}).update({{'ended_at': datetime.utcnow()}})\n")
        new_lines.append(f"{indent}db.commit()\n")
        
    new_lines.append(line)

with open(target_file, "w") as f:
    f.writelines(new_lines)

print("Enabled instant replay for simulations successfully.")
