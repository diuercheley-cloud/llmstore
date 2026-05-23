import React from 'react';
import { Paper, Typography } from '@mui/material';
import { Build as ToolIcon } from '@mui/icons-material';

const ToolNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'secondary.light', display: 'flex', alignItems: 'center' }}>
    <ToolIcon sx={{ mr: 1, color: 'secondary.main' }} />
    <Typography variant="body2">{label || 'Tool'}</Typography>
  </Paper>
);

export default ToolNode;
