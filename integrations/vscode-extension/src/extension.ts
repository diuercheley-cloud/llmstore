import * as vscode from 'vscode';

export async function activate(context: vscode.ExtensionContext) {
    const outputChannel = vscode.window.createOutputChannel("LLM Stack");

    const log = (message: string) => {
        // Redact potential secrets in logs
        const redacted = message.replace(/(api[_-]key|token|auth)=([^&\s]+)/gi, '$1=[REDACTED]');
        outputChannel.appendLine(`[${new Date().toISOString()}] ${redacted}`);
    };

    log("LLM Inference Stack Extension Activated");

    // Command: Connect
    let connectCmd = vscode.commands.registerCommand('llm-stack.connect', async () => {
        const apiKey = await vscode.window.showInputBox({
            prompt: "Enter your Admin API Key",
            password: true,
            ignoreFocusOut: true
        });

        if (apiKey) {
            await context.secrets.store('llmStack.apiKey', apiKey);
            vscode.window.showInformationMessage("LLM Stack: API Key saved securely.");
            log("API Key updated in SecretStorage");
        }
    });

    // Command: Run Workflow
    let runWorkflowCmd = vscode.commands.registerCommand('llm-stack.runWorkflow', async () => {
        const config = vscode.workspace.getConfiguration('llmStack');
        const apiBaseUrl = config.get<string>('apiBaseUrl');
        const apiKey = await context.secrets.get('llmStack.apiKey');

        if (!apiKey) {
            vscode.window.showErrorMessage("LLM Stack: API Key not found. Please use 'LLM Stack: Connect' first.");
            return;
        }

        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("LLM Stack: No active editor found.");
            return;
        }

        const workflowContent = editor.document.getText();
        log(`Running workflow from active editor at ${apiBaseUrl}`);

        try {
            // Simplified fetch-like logic (using node-fetch or similar would be better in a real app)
            // For now, we simulate the call or use internal vscode.http if available
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "LLM Stack: Running Workflow...",
                cancellable: false
            }, async (progress) => {
                // Mock API call to existing endpoint
                // In production, use axios or node-fetch
                log(`POST ${apiBaseUrl}/api/v1/admin/workflows/run`);
                // Simulate success
                await new Promise(r => setTimeout(r, 2000));
                vscode.window.showInformationMessage("LLM Stack: Workflow started successfully.");
            });
        } catch (err: any) {
            log(`Error running workflow: ${err.message}`);
            vscode.window.showErrorMessage(`LLM Stack: Failed to run workflow. ${err.message}`);
        }
    });

    // Command: Explain Selection
    let explainCmd = vscode.commands.registerCommand('llm-stack.explainSelection', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) { return; }

        const selection = editor.document.getText(editor.selection);
        if (!selection) {
            vscode.window.showWarningMessage("LLM Stack: Please select some text to explain.");
            return;
        }

        log("Explaining selection...");
        AgentChatPanel.createOrShow(context.extensionUri, selection);
    });

    // Command: Open Chat
    let openChatCmd = vscode.commands.registerCommand('llm-stack.openChat', () => {
        AgentChatPanel.createOrShow(context.extensionUri);
    });

    context.subscriptions.push(connectCmd, runWorkflowCmd, explainCmd, openChatCmd);
}

class AgentChatPanel {
    public static currentPanel: AgentChatPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, initialPrompt?: string) {
        const column = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.viewColumn : undefined;

        if (AgentChatPanel.currentPanel) {
            AgentChatPanel.currentPanel._panel.reveal(column);
            if (initialPrompt) {
                AgentChatPanel.currentPanel._panel.webview.postMessage({ command: 'setPrompt', text: initialPrompt });
            }
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'agentChat',
            'Agent Chat',
            column || vscode.ViewColumn.One,
            { enableScripts: true }
        );

        AgentChatPanel.currentPanel = new AgentChatPanel(panel, extensionUri, initialPrompt);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, initialPrompt?: string) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._update(initialPrompt);

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public dispose() {
        AgentChatPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) { x.dispose(); }
        }
    }

    private _update(initialPrompt?: string) {
        this._panel.webview.html = this._getHtmlForWebview(initialPrompt);
    }

    private _getHtmlForWebview(initialPrompt?: string) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Chat</title>
    <style>
        body { font-family: sans-serif; padding: 10px; }
        #chat { height: 300px; border: 1px solid #ccc; overflow-y: auto; margin-bottom: 10px; padding: 5px; }
        #input { width: 100%; box-sizing: border-box; }
    </style>
</head>
<body>
    <h3>LLM Stack Agent Chat</h3>
    <div id="chat"></div>
    <textarea id="input" rows="3" placeholder="Type a message...">${initialPrompt || ''}</textarea>
    <button id="send">Send</button>

    <script>
        const vscode = acquireVsCodeApi();
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        send.addEventListener('click', () => {
            const text = input.value;
            chat.innerHTML += '<div><b>You:</b> ' + text + '</div>';
            input.value = '';
            // In a real implementation, post to extension to call API
            setTimeout(() => {
                chat.innerHTML += '<div><b>Agent:</b> (Simulated response for: ' + text + ')</div>';
            }, 1000);
        });

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'setPrompt') {
                input.value = message.text;
            }
        });
    </script>
</body>
</html>`;
    }
}
