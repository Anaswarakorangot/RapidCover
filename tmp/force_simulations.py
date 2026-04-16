import os

target_file = r"c:\Users\Admin\Desktop\RapidCover\RapidCover\backend\app\api\admin.py"
with open(target_file, "r") as f:
    content = f.read()

# Force every simulation to create a NEW trigger event for demo purposes
# by ensuring we don't skip if 'existing' is found during a simulation call.

# This is a bit tricky to sed, so I'll use a python replacement
content = content.replace(
    'if not existing:',
    'if not existing or True: # HACKATHON_FORCE_FIRE'
)

with open(target_file, "w") as f:
    f.write(content)

print("Forced simulations to always fire fresh triggers.")
