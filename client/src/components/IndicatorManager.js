/* eslint-disable object-curly-spacing */
/* eslint-disable brace-style */
/* eslint-disable no-unused-vars */
/* eslint-disable max-len */
import React, {useState, useEffect, useRef, useCallback} from 'react';
import {Box, IconButton, Button, Typography, TextField, Collapse,
  List, ListItem, ListItemText, ListItemSecondaryAction, Switch,
  Chip, Tab, Tabs, LinearProgress, Paper, Dialog, DialogTitle,
  DialogContent, DialogActions, CircularProgress} from '@mui/material';
import PropTypes from 'prop-types';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SendIcon from '@mui/icons-material/Send';
import withStyles from '@mui/styles/withStyles';
import {FormattedMessage} from 'react-intl';
import ChatFormRenderer from './ChatFormRenderer';
import ChatHistoryDialog from './ChatHistoryDialog';
import HistoryIcon from '@mui/icons-material/History';

const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 20px',
    backgroundColor: '#24323c',
    color: '#fff',
    minHeight: '64px',
  },
  main: {
    padding: '16px',
    maxWidth: '400px',
    height: 'calc(100vh - 64px)',
    overflow: 'auto',
  },
  dropZone: {
    border: '2px dashed #90caf9',
    borderRadius: '8px',
    padding: '24px',
    textAlign: 'center',
    cursor: 'pointer',
    backgroundColor: '#fafafa',
    transition: 'all 0.2s',
    marginBottom: '16px',
    '&:hover': {
      backgroundColor: '#e3f2fd',
      borderColor: '#1976d2',
    },
  },
  dropZoneActive: {
    border: '2px dashed #1976d2',
    backgroundColor: '#e3f2fd',
  },
  chatMessage: {
    padding: '10px 14px',
    marginBottom: '8px',
    borderRadius: '12px',
    maxWidth: '90%',
    wordWrap: 'break-word',
    whiteSpace: 'pre-wrap',
    fontSize: '0.9rem',
    lineHeight: 1.5,
  },
  userMessage: {
    backgroundColor: '#1976d2',
    color: '#fff',
    marginLeft: 'auto',
    borderBottomRightRadius: '4px',
  },
  assistantMessage: {
    backgroundColor: '#f5f5f5',
    color: '#333',
    borderBottomLeftRadius: '4px',
  },
  indicatorItem: {
    borderBottom: '1px solid #eee',
    '&:last-child': {borderBottom: 'none'},
  },
};

const API_BASE = '/mind';

const IndicatorManager = (props) => {
  const {classes, closeDrawer, onIndicatorAdded} = props;
  const [activeTab, setActiveTab] = useState(0);
  const [indicators, setIndicators] = useState([]);
  const [expandedIndicator, setExpandedIndicator] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [loadingIndicators, setLoadingIndicators] = useState(false);
  const [chatHistoryDialog, setChatHistoryDialog] = useState(null);
  const [chatHistoryMessages, setChatHistoryMessages] = useState([]);

  // Chat state
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [formSubmitted, setFormSubmitted] = useState({});
  const [addedToDashboard, setAddedToDashboard] = useState(new Set());
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const fetchIndicators = useCallback(async () => {
    setLoadingIndicators(true);
    try {
      const resp = await fetch(`${API_BASE}/indicators`);
      const data = await resp.json();
      setIndicators(data.indicators || []);
    } catch (e) {
      console.error('Failed to fetch indicators:', e);
    }
    setLoadingIndicators(false);
  }, []);

  useEffect(() => {
    fetchIndicators();
  }, [fetchIndicators]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({behavior: 'smooth'});
  }, [messages]);

  const handleFileUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    setSending(true);
    setProgress(10);
    setProgressMsg('Uploading file...');

    try {
      const resp = await fetch(`${API_BASE}/upload`, {method: 'POST', body: formData});
      const data = await resp.json();
      setSessionId(data.session_id);

      const cols = data.validation.columns || [];
      const rows = (data.sample_rows || []).slice(0, 3);
      const previewCols = cols.slice(0, 6);
      const hasMore = cols.length > 6;
      let tableHtml = '';
      if (rows.length > 0) {
        tableHtml = '<table style="width:100%;border-collapse:collapse;font-size:0.75rem;margin:8px 0">' +
          '<tr>' + previewCols.map((c) => `<th style="border:1px solid #ccc;padding:3px 6px;background:#eee;text-align:left">${c}</th>`).join('') + '</tr>' +
          rows.map((r) => '<tr>' + previewCols.map((c) => `<td style="border:1px solid #ddd;padding:3px 6px">${r[c] != null ? r[c] : ''}</td>`).join('') + '</tr>').join('') +
          '</table>' + (hasMore ? `<em style="font-size:0.75rem">... and ${cols.length - 6} more columns</em>` : '');
      }

      const summary = `File received: **${file.name}** (${data.validation.row_count} rows, ${cols.length} columns)` +
        `\n\nColumns: ${cols.join(', ')}` +
        (data.validation.sheets ? `\n\nSheets: ${data.validation.sheets.join(', ')}` : '') +
        (data.validation.issues.length > 0 ? `\n\nIssues: ${data.validation.issues.join(', ')}` : '');

      setMessages((prev) => [
        ...prev,
        {role: 'user', content: `Uploaded: ${file.name}`},
        {role: 'assistant', content: summary, tableHtml},
      ]);
    } catch (e) {
      setMessages((prev) => [...prev, {role: 'assistant', content: `Error uploading file: ${e.message}`}]);
    }
    setSending(false);
    setProgress(0);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const processChatResponse = async (resp) => {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistantText = '';
    let files = [];
    let formData = null;
    let indicatorCreated = false;

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'progress') {
            setProgress(event.progress);
            setProgressMsg(event.message);
          } else if (event.type === 'response') {
            assistantText = event.text;
            files = event.files || [];
            formData = event.form || null;
            indicatorCreated = event.indicator_created || false;
          } else if (event.type === 'error') {
            assistantText = `Error: ${event.message}`;
          }
        } catch (parseErr) {
          // skip malformed SSE
        }
      }
    }

    setMessages((prev) => [...prev, {role: 'assistant', content: assistantText, form: formData, showAddButton: indicatorCreated}]);

    if (indicatorCreated) {
      fetchIndicators();
    }
  };

  const sendChatMessage = async (message) => {
    setSending(true);
    setProgress(5);
    setProgressMsg('Thinking...');
    try {
      const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: sessionId, message, api_key: apiKey || null}),
      });
      await processChatResponse(resp);
    } catch (e) {
      setMessages((prev) => [...prev, {role: 'assistant', content: `Error: ${e.message}`}]);
    }
    setSending(false);
    setProgress(0);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || !sessionId) return;
    const msg = inputText.trim();
    setInputText('');
    setMessages((prev) => [...prev, {role: 'user', content: msg}]);
    await sendChatMessage(msg);
  };

  const handleFormSubmit = async (formResponse) => {
    setFormSubmitted((prev) => ({...prev, [formResponse.form_id]: true}));
    const summary = Object.entries(formResponse.values)
        .map(([k, v]) => `${k}: ${v}`).join('\n');
    setMessages((prev) => [...prev, {role: 'user', content: summary}]);
    await sendChatMessage(formResponse);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleHide = async (indicatorId, currentHidden) => {
    await fetch(`${API_BASE}/indicators/${indicatorId}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({hidden: !currentHidden}),
    });
    fetchIndicators();
    if (onIndicatorAdded) onIndicatorAdded();
  };

  const openChatHistory = async (ind) => {
    setChatHistoryDialog(ind);
    setChatHistoryMessages([]);
    try {
      const resp = await fetch(`${API_BASE}/indicators/${ind.id}/chat`);
      const data = await resp.json();
      setChatHistoryMessages(data.messages || []);
    } catch (e) {
      setChatHistoryMessages([]);
    }
  };

  const confirmDelete = async () => {
    if (!deleteDialog || deleteConfirmText !== deleteDialog.id) return;
    await fetch(`${API_BASE}/indicators/${deleteDialog.id}`, {method: 'DELETE'});
    setDeleteDialog(null);
    setDeleteConfirmText('');
    fetchIndicators();
  };

  const renderMessage = (msg, idx) => {
    const isUser = msg.role === 'user';
    const content = msg.content
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:4px;margin-top:8px"/>')
        .replace(/\n/g, '<br/>');
    return (
      <Box key={idx} sx={{mb: 1}}>
        <Box sx={{display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start'}}>
          <Paper
            elevation={0}
            className={`${classes.chatMessage} ${isUser ? classes.userMessage : classes.assistantMessage}`}
          >
            <span dangerouslySetInnerHTML={{__html: content}} />
            {msg.tableHtml && <div dangerouslySetInnerHTML={{__html: msg.tableHtml}} />}
          </Paper>
        </Box>
        {msg.form && !isUser && (
          <ChatFormRenderer
            form={msg.form}
            onSubmit={handleFormSubmit}
            disabled={sending || !!formSubmitted[msg.form.id]}
          />
        )}
        {msg.showAddButton && !isUser && (
          <Box sx={{mt: 1, display: 'flex', justifyContent: 'flex-start'}}>
            <Button
              variant="contained"
              size="small"
              disabled={addedToDashboard.has(idx)}
              onClick={() => {
                setAddedToDashboard((prev) => new Set([...prev, idx]));
                if (onIndicatorAdded) onIndicatorAdded();
              }}
              sx={{
                textTransform: 'none',
                backgroundColor: addedToDashboard.has(idx) ? '#4caf50' : '#1976d2',
                '&:disabled': {backgroundColor: '#4caf50', color: '#fff'},
              }}
            >
              {addedToDashboard.has(idx) ? 'Added to Dashboard' : 'Add to Dashboard'}
            </Button>
          </Box>
        )}
      </Box>
    );
  };

  return (
    <main>
      <div className={classes.header}>
        <IconButton onClick={closeDrawer}>
          <ChevronRightIcon style={{color: 'gold'}}/>
        </IconButton>
        <Typography variant="subtitle1" style={{color: '#fff', fontWeight: 'bold'}}>
          <FormattedMessage id='indicator_manager' defaultMessage='Manage Indicators'/>
        </Typography>
      </div>

      <Box sx={{borderBottom: 1, borderColor: 'divider'}}>
        <Tabs value={activeTab} onChange={(e, v) => { setActiveTab(v); if (v === 0) fetchIndicators(); }} variant="fullWidth">
          <Tab label={<FormattedMessage id='indicator_list' defaultMessage='Indicator List'/>} />
          <Tab label={<FormattedMessage id='add_indicator' defaultMessage='Add Indicator'/>} />
        </Tabs>
      </Box>

      {/* Tab 1: Indicator List */}
      {activeTab === 0 && (
        <div className={classes.main}>
          {loadingIndicators && <LinearProgress />}
          {indicators.length === 0 && !loadingIndicators && (
            <Typography variant="body2" color="textSecondary" style={{textAlign: 'center', marginTop: '40px'}}>
              No user-created indicators yet. Use the "Add Indicator" tab to create one.
            </Typography>
          )}
          <List>
            {indicators.map((ind) => (
              <React.Fragment key={ind.id}>
                <ListItem
                  button
                  onClick={() => setExpandedIndicator(expandedIndicator === ind.id ? null : ind.id)}
                  className={classes.indicatorItem}
                >
                  <ListItemText
                    primary={
                      <Box sx={{display: 'flex', alignItems: 'center', gap: 1}}>
                        <Typography variant="subtitle2">{ind.display_name}</Typography>
                        <Chip label={ind.is_user_created ? 'Custom' : 'Default'} size="small"
                          color={ind.is_user_created ? 'primary' : 'default'}
                          style={{height: 20, fontSize: '0.7rem'}}
                        />
                        {ind.hidden && <Chip label="Not Listed" size="small" color="warning" style={{height: 20, fontSize: '0.7rem'}}/>}
                      </Box>
                    }
                    secondary={ind.country}
                  />
                  {expandedIndicator === ind.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </ListItem>
                <Collapse in={expandedIndicator === ind.id}>
                  <Box sx={{px: 2, py: 1, backgroundColor: '#fafafa'}}>
                    {ind.description && (
                      <Typography variant="body2" paragraph>{ind.description}</Typography>
                    )}
                    <Typography variant="caption" display="block" color="textSecondary">
                      Subgroups: {(ind.subgroups || []).join(', ')}
                    </Typography>
                    <Typography variant="caption" display="block" color="textSecondary">
                      Version: {ind.version} | Theme: {ind.color_theme}
                    </Typography>
                    {ind.created_at && (
                      <Typography variant="caption" display="block" color="textSecondary">
                        Created: {new Date(ind.created_at).toLocaleDateString()}
                      </Typography>
                    )}
                    {ind.onboarding_notes && (
                      <Typography variant="caption" display="block" color="textSecondary" style={{marginTop: 4}}>
                        Notes: {ind.onboarding_notes}
                      </Typography>
                    )}
                    {ind.is_user_created && (
                      <Box sx={{mt: 1, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap'}}>
                        <Button
                          size="small"
                          startIcon={<HistoryIcon />}
                          onClick={() => openChatHistory(ind)}
                          variant="outlined"
                        >
                          Chat History
                        </Button>
                        <Button
                          size="small"
                          startIcon={ind.hidden ? <VisibilityIcon /> : <VisibilityOffIcon />}
                          onClick={() => toggleHide(ind.id, ind.hidden)}
                          variant="outlined"
                        >
                          {ind.hidden ? 'Add to Dashboard' : 'Remove from Dashboard'}
                        </Button>
                        <Button
                          size="small"
                          startIcon={<DeleteIcon />}
                          onClick={() => setDeleteDialog(ind)}
                          variant="outlined"
                          color="error"
                        >
                          Delete
                        </Button>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </React.Fragment>
            ))}
          </List>
        </div>
      )}

      {/* Tab 2: AI Chat */}
      {activeTab === 1 && (
        <div className={classes.main} style={{display: 'flex', flexDirection: 'column', maxWidth: '33vw', minWidth: '400px'}}>
          {/* API Key */}
          <Box sx={{mb: 2, p: 1, backgroundColor: '#fff3cd', borderRadius: 1, border: '1px solid #ffc107'}}>
            <Typography variant="caption" sx={{color: '#856404'}}>Anthropic API Key</Typography>
            <TextField
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter Anthropic API key"
              fullWidth size="small"
              style={{backgroundColor: 'white', marginTop: 4}}
            />
          </Box>

          {/* Drop zone */}
          {!sessionId && (
            <Box
              className={`${classes.dropZone} ${dragOver ? classes.dropZoneActive : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
            >
              <CloudUploadIcon style={{fontSize: 48, color: '#90caf9'}} />
              <Typography variant="body2" color="textSecondary" style={{marginTop: 8}}>
                <FormattedMessage id='upload_file' defaultMessage='Drag & drop a CSV or Excel file here'/>
              </Typography>
              <Typography variant="caption" color="textSecondary">
                or click to browse
              </Typography>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                style={{display: 'none'}}
                onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])}
              />
            </Box>
          )}

          {/* Progress bar */}
          {sending && (
            <Box sx={{mb: 1}}>
              <LinearProgress variant="determinate" value={progress} />
              <Typography variant="caption" color="textSecondary">{progressMsg}</Typography>
            </Box>
          )}

          {/* Chat messages */}
          <Box sx={{flex: 1, overflow: 'auto', mb: 1, minHeight: '200px'}}>
            {messages.map((msg, idx) => renderMessage(msg, idx))}
            <div ref={chatEndRef} />
          </Box>

          {/* Input area */}
          {sessionId && (
            <Box sx={{display: 'flex', gap: 1, alignItems: 'flex-end'}}>
              <TextField
                fullWidth
                multiline
                maxRows={4}
                size="small"
                placeholder="Describe your indicator..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={sending}
              />
              <IconButton color="primary" onClick={sendMessage} disabled={sending || !inputText.trim()}>
                {sending ? <CircularProgress size={24} /> : <SendIcon />}
              </IconButton>
            </Box>
          )}
        </div>
      )}

      <ChatHistoryDialog
        open={!!chatHistoryDialog}
        onClose={() => setChatHistoryDialog(null)}
        messages={chatHistoryMessages}
        indicatorName={chatHistoryDialog?.display_name}
      />

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteDialog} onClose={() => setDeleteDialog(null)}>
        <DialogTitle>Delete Indicator</DialogTitle>
        <DialogContent>
          <Typography variant="body2" paragraph>
            This will permanently delete <strong>{deleteDialog?.display_name}</strong> and all its data.
          </Typography>
          <Typography variant="body2" paragraph>
            <FormattedMessage id='delete_confirm' defaultMessage='Type indicator name to confirm deletion'/>:
          </Typography>
          <TextField
            fullWidth size="small"
            placeholder={deleteDialog?.id}
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {setDeleteDialog(null); setDeleteConfirmText('');}}>Cancel</Button>
          <Button
            color="error" variant="contained"
            disabled={deleteConfirmText !== deleteDialog?.id}
            onClick={confirmDelete}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </main>
  );
};

IndicatorManager.propTypes = {
  classes: PropTypes.object,
  closeDrawer: PropTypes.func,
  onIndicatorAdded: PropTypes.func,
};

export default withStyles(styles)(IndicatorManager);
