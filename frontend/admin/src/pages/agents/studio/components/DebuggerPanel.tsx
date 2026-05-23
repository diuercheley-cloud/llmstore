import React from 'react';
import { Box, Typography, Paper, Divider, Chip } from '@mui/material';

const DebuggerPanel: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>Run Debugger</Typography>
      
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="subtitle1">Run: run_7890 (Active)</Typography>
          <Chip label="Executing" color="info" size="small" />
        </Box>
        <Divider />
        <Box sx={{ py: 2 }}>
          <Typography variant="body2" color="text.secondary">Step 1: Start</Typography>
          <Typography variant="body2" color="text.secondary">Step 2: Thinking...</Typography>
        </Box>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>Trace Inspector</Typography>
        <Box sx={{ bgcolor: 'black', color: '#00ff00', p: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>
          {`[10:00:01] INFO: Initializing flow\n[10:00:02] INFO: ReAct step triggered\n[10:00:03] INFO: Tool call: list_files\n[10:00:04] INFO: Observation received`}
        </Box>
      </Paper>
    </Box>
  );
};

export default DebuggerPanel;
