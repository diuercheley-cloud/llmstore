import React from 'react';
import { Paper, Typography } from '@mui/material';
import { Forward as HandoffIcon } from '@mui/icons-material';

const HandoffNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderStyle: 'dashed', display: 'flex', alignItems: 'center' }}>
    <HandoffIcon sx={{ mr: 1, color: 'text.secondary' }} />
    <Typography variant="body2">{label || 'Handoff'}</Typography>
  </Paper>
);

export default HandoffNode;
