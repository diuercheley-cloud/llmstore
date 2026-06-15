import re

with open('frontend/admin/src/pages/observability/RealtimeDashboard.tsx') as f:
    content = f.read()

pattern = re.compile(r'(  const MetricCard =.*?  \)\n)', re.DOTALL)
match = pattern.search(content)
if match:
    card_code = match.group(1)
    content = content.replace(card_code, '')
    
    card_code = '\n'.join([line[2:] if line.startswith('  ') else line for line in card_code.split('\n')])
    
    content = content.replace('export default function RealtimeDashboard() {', card_code + '\nexport default function RealtimeDashboard() {')
    
    with open('frontend/admin/src/pages/observability/RealtimeDashboard.tsx', 'w') as f:
        f.write(content)
    print("Fixed RealtimeDashboard.tsx")
else:
    print("Could not find MetricCard code.")

