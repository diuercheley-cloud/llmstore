import re

with open('frontend/admin/src/pages/AgentApprovals.tsx') as f:
    content = f.read()

# Extract RiskBadge and StatusBadge (they are side by side)
pattern = re.compile(r'(  // Risk Badge component.*?  }\n\n  // Status Badge component.*?  }\n)', re.DOTALL)
match = pattern.search(content)
if match:
    badges_code = match.group(1)
    # Remove them from inside the component
    content = content.replace(badges_code, '')
    
    # Unindent
    badges_code = '\n'.join([line[2:] if line.startswith('  ') else line for line in badges_code.split('\n')])
    
    # Insert before export default
    content = content.replace('export default function AgentApprovals() {', badges_code + '\nexport default function AgentApprovals() {')
    
    with open('frontend/admin/src/pages/AgentApprovals.tsx', 'w') as f:
        f.write(content)
    print("Fixed AgentApprovals.tsx")
else:
    print("Could not find badges code.")

