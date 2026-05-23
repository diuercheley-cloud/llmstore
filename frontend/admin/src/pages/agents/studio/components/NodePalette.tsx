import React from 'react';
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  Paper 
} from '@mui/material';
import { 
  SmartToy as AgentIcon,
  Build as ToolIcon,
  Storage as MemoryIcon,
  Verified as ApprovalIcon,
  AltRoute as ConditionIcon,
  Forward as HandoffIcon,
  Flag as FinalIcon
} from '@mui/icons-material';

const nodeTypes = [
  { label: 'Agent', icon: <AgentIcon />, type: 'agent' },
  { label: 'Tool Call', icon: <ToolIcon />, type: 'tool_call' },
  { label: 'Memory', icon: <MemoryIcon />, type: 'memory' },
  { label: 'Approval', icon: <ApprovalIcon />, type: 'approval' },
  { label: 'Condition', icon: <ConditionIcon />, type: 'condition' },
  { label: 'Handoff', icon: <HandoffIcon />, type: 'handoff' },
  { label: 'Final', icon: <FinalIcon />, type: 'final' },
];

const NodePalette: React.FC = () => {
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="overline" color="text.secondary">Nodes</Typography>
      <List dense>
        {nodeTypes.map((n) => (
          <ListItem 
            key={n.type} 
            component={Paper} 
            sx={{ mb: 1, cursor: 'grab', '&:hover': { bgcolor: 'action.hover' } }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{n.icon}</ListItemIcon>
            <ListItemText primary={n.label} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default NodePalette;
