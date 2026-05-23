import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Chip, 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableRow, 
  IconButton,
  LinearProgress,
  Divider
} from '@mui/material';
import { 
  Activity, 
  Wrench, 
  Database, 
  UserCheck, 
  Coins, 
  AlertTriangle,
  Info,
  Play
} from 'lucide-react';

export const AgenticOperationsDashboard: React.FC = () => {
    return (
        <Box sx={{ p: 3, maxWidth: '1600px', margin: '0 auto' }}>
            <header style={{ marginBottom: '32px' }}>
                <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.02em' }}>
                    Agentic <span style={{ color: '#3f51b5' }}>Operations</span>
                </Typography>
                <Typography variant="subtitle1" color="text.secondary">
                    Monitoramento em tempo real de autonomia, custos e conformidade.
                </Typography>
            </header>

            <Grid container spacing={3}>
                {/* Platform Health Summary */}
                <Grid item xs={12} md={3}>
                    <Paper sx={{ p: 3, borderRadius: '24px', height: '100%', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none', bgcolor: '#f8f9fa' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                            <Activity color="#3f51b5" />
                            <Typography variant="h6" fontWeight="bold">Platform Health</Typography>
                        </Box>
                        <Box sx={{ spaceY: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                <Typography variant="body2" fontWeight="bold">OBSERVABILITY</Typography>
                                <Chip label="ENABLED" color="success" size="small" sx={{ fontWeight: 'black', fontSize: '10px' }} />
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                <Typography variant="body2" fontWeight="bold">GUARDRAILS</Typography>
                                <Chip label="ACTIVE" color="success" size="small" sx={{ fontWeight: 'black', fontSize: '10px' }} />
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2" fontWeight="bold">AUTO-RECOVERY</Typography>
                                <Chip label="DISABLED" color="error" size="small" sx={{ fontWeight: 'black', fontSize: '10px' }} />
                            </Box>
                        </Box>
                    </Paper>
                </Grid>

                {/* Key Metrics Row */}
                <Grid item xs={12} md={9}>
                    <Grid container spacing={3}>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 3, borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none' }}>
                                <Typography variant="overline" fontWeight="bold" color="text.secondary">Tool Latency (Avg)</Typography>
                                <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, mt: 1 }}>
                                    <Typography variant="h4" fontWeight="black">452ms</Typography>
                                    <Typography variant="body2" color="success.main" fontWeight="bold">-12%</Typography>
                                </Box>
                                <LinearProgress variant="determinate" value={45} sx={{ mt: 2, height: 6, borderRadius: 3 }} />
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 3, borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none' }}>
                                <Typography variant="overline" fontWeight="bold" color="text.secondary">Memory Hit Rate</Typography>
                                <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, mt: 1 }}>
                                    <Typography variant="h4" fontWeight="black">89.4%</Typography>
                                    <Typography variant="body2" color="success.main" fontWeight="bold">+2.1%</Typography>
                                </Box>
                                <LinearProgress variant="determinate" value={89} color="success" sx={{ mt: 2, height: 6, borderRadius: 3 }} />
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 3, borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none' }}>
                                <Typography variant="overline" fontWeight="bold" color="text.secondary">Approval Backlog</Typography>
                                <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, mt: 1 }}>
                                    <Typography variant="h4" fontWeight="black">12</Typography>
                                    <Typography variant="body2" color="warning.main" fontWeight="bold">Waiting</Typography>
                                </Box>
                                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                                    <Chip label="High Risk: 3" size="small" color="error" sx={{ fontSize: '10px' }} />
                                    <Chip label="Medium: 9" size="small" color="warning" sx={{ fontSize: '10px' }} />
                                </Box>
                            </Paper>
                        </Grid>
                    </Grid>
                </Grid>

                {/* Active Agents Table */}
                <Grid item xs={12} lg={8}>
                    <Paper sx={{ p: 0, borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none' }}>
                        <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: '#f8f9fa' }}>
                            <Typography variant="h6" fontWeight="black" sx={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}>Active Agents</Typography>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Chip label="TOTAL: 42" size="small" variant="outlined" />
                                <Chip label="RUNNING: 18" size="small" color="primary" />
                            </Box>
                        </Box>
                        <Table>
                            <TableHead sx={{ bgcolor: 'rgba(0,0,0,0.02)' }}>
                                <TableRow>
                                    <TableCell sx={{ fontWeight: 'bold' }}>AGENT</TableCell>
                                    <TableCell sx={{ fontWeight: 'bold' }}>STATUS</TableCell>
                                    <TableCell sx={{ fontWeight: 'bold' }}>SUCCESS RATE</TableCell>
                                    <TableCell sx={{ fontWeight: 'bold' }}>COST (MTD)</TableCell>
                                    <TableCell sx={{ fontWeight: 'bold' }}>ACTIONS</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                <TableRow hover>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography variant="body2" fontWeight="bold">CustomerSupportV2</Typography>
                                            <Typography variant="caption" color="text.secondary">#a82b</Typography>
                                        </Box>
                                    </TableCell>
                                    <TableCell><Chip label="production" color="success" size="small" sx={{ fontWeight: 'bold', fontSize: '10px' }} /></TableCell>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography variant="body2" fontWeight="bold">98.2%</Typography>
                                            <Box sx={{ width: 40, height: 4, bgcolor: '#eee', borderRadius: 2, overflow: 'hidden' }}>
                                                <Box sx={{ width: '98%', height: '100%', bgcolor: 'success.main' }} />
                                            </Box>
                                        </Box>
                                    </TableCell>
                                    <TableCell>R$ 1.242,50</TableCell>
                                    <TableCell>
                                        <IconButton size="small"><Info size={16} /></IconButton>
                                        <IconButton size="small" color="primary"><Play size={16} /></IconButton>
                                    </TableCell>
                                </TableRow>
                                <TableRow hover>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography variant="body2" fontWeight="bold">SalesLeadGenerator</Typography>
                                            <Typography variant="caption" color="text.secondary">#c41d</Typography>
                                        </Box>
                                    </TableCell>
                                    <TableCell><Chip label="staging" color="warning" size="small" sx={{ fontWeight: 'bold', fontSize: '10px' }} /></TableCell>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography variant="body2" fontWeight="bold">85.0%</Typography>
                                            <Box sx={{ width: 40, height: 4, bgcolor: '#eee', borderRadius: 2, overflow: 'hidden' }}>
                                                <Box sx={{ width: '85%', height: '100%', bgcolor: 'warning.main' }} />
                                            </Box>
                                        </Box>
                                    </TableCell>
                                    <TableCell>R$ 430,20</TableCell>
                                    <TableCell>
                                        <IconButton size="small"><Info size={16} /></IconButton>
                                        <IconButton size="small" color="primary"><Play size={16} /></IconButton>
                                    </TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </Paper>
                </Grid>

                {/* Sidebar: Budget & Incidents */}
                <Grid item xs={12} lg={4}>
                    <Box sx={{ spaceY: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {/* Budget Usage */}
                        <Paper sx={{ p: 3, borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none', bgcolor: '#1a1a1a', color: 'white' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                                <Coins color="#4caf50" />
                                <Typography variant="h6" fontWeight="bold">Budget Usage</Typography>
                            </Box>
                            <Box sx={{ mb: 3 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="caption" sx={{ opacity: 0.7 }}>MONTHLY LIMIT (BRL)</Typography>
                                    <Typography variant="caption" fontWeight="bold">R$ 5.000 / R$ 10.000</Typography>
                                </Box>
                                <LinearProgress variant="determinate" value={50} color="success" sx={{ height: 8, borderRadius: 4, bgcolor: 'rgba(255,255,255,0.1)' }} />
                            </Box>
                            <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="caption" sx={{ opacity: 0.7 }}>TOKEN QUOTA</Typography>
                                    <Typography variant="caption" fontWeight="bold">820M / 1.000M</Typography>
                                </Box>
                                <LinearProgress variant="determinate" value={82} color="warning" sx={{ height: 8, borderRadius: 4, bgcolor: 'rgba(255,255,255,0.1)' }} />
                            </Box>
                        </Paper>

                        {/* Incident Timeline */}
                        <Paper sx={{ p: 3, borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: 'none' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                                <AlertTriangle color="#f44336" />
                                <Typography variant="h6" fontWeight="bold">Incident Timeline</Typography>
                            </Box>
                            <Box sx={{ position: 'relative', pl: 3, borderLeft: '2px solid #eee' }}>
                                <Box sx={{ mb: 3, position: 'relative' }}>
                                    <Box sx={{ position: 'absolute', left: -31, top: 0, width: 14, height: 14, borderRadius: '50%', bgcolor: '#f44336', border: '3px solid white' }} />
                                    <Typography variant="caption" color="text.secondary">14:22 - HIGH SEVERITY</Typography>
                                    <Typography variant="body2" fontWeight="bold">CustomerSupportV2: Tool failure loop detected.</Typography>
                                    <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>Action: Automated pause initiated.</Typography>
                                </Box>
                                <Box sx={{ mb: 3, position: 'relative' }}>
                                    <Box sx={{ position: 'absolute', left: -31, top: 0, width: 14, height: 14, borderRadius: '50%', bgcolor: '#ff9800', border: '3px solid white' }} />
                                    <Typography variant="caption" color="text.secondary">10:05 - MEDIUM</Typography>
                                    <Typography variant="body2" fontWeight="bold">Quota breach warning: SalesLeadGenerator.</Typography>
                                </Box>
                                <Box sx={{ position: 'relative' }}>
                                    <Box sx={{ position: 'absolute', left: -31, top: 0, width: 14, height: 14, borderRadius: '50%', bgcolor: '#4caf50', border: '3px solid white' }} />
                                    <Typography variant="caption" color="text.secondary">Yesterday - RESOLVED</Typography>
                                    <Typography variant="body2" fontWeight="bold">Memory sync latency normalized.</Typography>
                                </Box>
                            </Box>
                        </Paper>
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
};

export default AgenticOperationsDashboard;
