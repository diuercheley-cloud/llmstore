import React, { useState } from 'react';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import { 
  Build as BuildIcon, 
  BugReport as BugIcon, 
  Save as SaveIcon,
  PlayArrow as PlayIcon
} from '@mui/icons-material';
import FlowBuilder from './components/FlowBuilder';
import DebuggerPanel from './components/DebuggerPanel';

const AgentStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'builder' | 'debugger'>('builder');

  return (
    <Box sx={{ flexGrow: 1, height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">Agent Studio</Typography>
        <Box>
          <Button 
            startIcon={<BuildIcon />} 
            variant={activeTab === 'builder' ? 'contained' : 'outlined'} 
            onClick={() => setActiveTab('builder')}
            sx={{ mr: 1 }}
          >
            Builder
          </Button>
          <Button 
            startIcon={<BugIcon />} 
            variant={activeTab === 'debugger' ? 'contained' : 'outlined'} 
            onClick={() => setActiveTab('debugger')}
          >
            Debugger
          </Button>
        </Box>
      </Box>

      <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
        {activeTab === 'builder' ? (
          <FlowBuilder />
        ) : (
          <DebuggerPanel />
        )}
      </Box>
    </Box>
  );
};

export default AgentStudio;
