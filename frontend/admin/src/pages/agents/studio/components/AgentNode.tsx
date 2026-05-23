import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { SmartToy as AgentIcon } from '@mui/icons-material';

const AgentNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'primary.light', display: 'flex', alignItems: 'center' }}>
    <AgentIcon sx={{ mr: 1, color: 'primary.main' }} />
    <Typography variant="body2">{label || 'Agent'}</Typography>
  </Paper>
);

export default AgentNode;
