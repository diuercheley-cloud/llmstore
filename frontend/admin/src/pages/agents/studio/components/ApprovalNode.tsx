import React from 'react';
import { Paper, Typography } from '@mui/material';
import { Verified as ApprovalIcon } from '@mui/icons-material';

const ApprovalNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'warning.light', display: 'flex', alignItems: 'center' }}>
    <ApprovalIcon sx={{ mr: 1, color: 'warning.main' }} />
    <Typography variant="body2">{label || 'Approval'}</Typography>
  </Paper>
);

export default ApprovalNode;
