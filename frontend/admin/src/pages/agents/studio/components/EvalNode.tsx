import React from 'react';
import { Paper, Typography } from '@mui/material';
import { Security as EvalIcon } from '@mui/icons-material';

const EvalNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'success.light', display: 'flex', alignItems: 'center' }}>
    <EvalIcon sx={{ mr: 1, color: 'success.main' }} />
    <Typography variant="body2">{label || 'Eval'}</Typography>
  </Paper>
);

export default EvalNode;
