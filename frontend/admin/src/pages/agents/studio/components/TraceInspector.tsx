import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const TraceInspector: React.FC<{ events?: any[] }> = ({ events }) => (
  <Box sx={{ p: 2 }}>
    <Typography variant="overline">Trace Inspector</Typography>
    <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto', p: 1, bgcolor: 'grey.900', color: 'common.white', fontFamily: 'monospace', fontSize: '0.75rem' }}>
      {(events || [
        { time: "10:00:01", msg: "Event: run_started" },
        { time: "10:00:05", msg: "Event: thought_generated", summary: "Analyzing the user request..." }
      ]).map((e, i) => (
        <Box key={i} sx={{ mb: 1 }}>
          <Typography variant="caption" color="grey.500">[{e.time}] </Typography>
          <Typography variant="caption" sx={{ color: 'primary.light' }}>{e.msg} </Typography>
          {e.summary && <Typography variant="caption" sx={{ color: 'grey.300' }}>- {e.summary}</Typography>}
        </Box>
      ))}
    </Paper>
  </Box>
);

export default TraceInspector;
