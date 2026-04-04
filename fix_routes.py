import sys

path = 'backend/app/api/zones.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

router_decl = 'router = APIRouter(prefix="/zones", tags=["zones"])'
parts = content.split(router_decl)

if len(parts) < 2:
    print('router decl not found')
    sys.exit(1)

header = parts[0] + router_decl + '\n\n'
body = parts[1]

reassign_marker = '# =============================================================================\n# Zone Reassignment 24-Hour Workflow Endpoints\n# =============================================================================\n'

body_parts = body.split(reassign_marker)
if len(body_parts) > 1:
    old_routes = body_parts[0]
    new_routes = reassign_marker + body_parts[1]
    
    new_content = header + new_routes + '\n\n' + old_routes
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Routing fixed!')
else:
    print('Reassign marker not found')
