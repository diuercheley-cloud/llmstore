import React from 'react';
import { Paper, Typography } from '@mui/material';
import { AltRoute as ConditionIcon } from '@mui/icons-material';

const ConditionNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', borderRadius: '20px' }}>
    <ConditionIcon sx={{ mr: 1 }} />
    <Typography variant="body2">{label || 'Condition'}</Typography>
  </Paper>
);

export default ConditionNode;
