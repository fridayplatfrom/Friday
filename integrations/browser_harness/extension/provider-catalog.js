// Shared, declarative website contracts. No credentials or executable repairs.
(()=>{const freeze=value=>{if(value&&typeof value==='object'){for(const item of Object.values(value))freeze(item);Object.freeze(value);}return value;};globalThis.FridayProviderCatalog=freeze({
  "chatgpt-web": {
    "id": "chatgpt-web",
    "provisionalConversationPath": "^/c/local-chatgpt(?:%3[Aa]|:)",
    "name": "ChatGPT",
    "url": "https://chatgpt.com/",
    "revision": 1,
    "experimental": false,
    "backup": false,
    "capabilities": {
      "text": true,
      "toolProtocol": true,
      "imageInput": true,
      "imageOutput": true,
      "fileTransfer": true,
      "twoWay": true
    },
    "selectors": {
      "hosts": [
        "chatgpt.com"
      ],
      "composer": [
        "#prompt-textarea",
        "#mobile-composer-prompt",
        "[contenteditable=\"true\"][role=\"textbox\"][aria-label=\"Ask ChatGPT\"]",
        "textarea[placeholder*=\"Ask\"]"
      ],
      "send": [
        "button[data-testid=\"send-button\"]",
        "button[aria-label=\"Send prompt\"]",
        "button[aria-label=\"Send message\"]",
        "button[aria-label=\"Send\"]"
      ],
      "responses": [
        "[data-message-author-role=\"assistant\"]",
        "[data-markdown-text-style=\"assistant-message\"]"
      ],
      "stop": [
        "button[data-testid=\"stop-button\"]",
        "button[aria-label=\"Stop generating\"]",
        "button[aria-label=\"Stop streaming\"]",
        "button[aria-label=\"Stop\"]"
      ],
      "complete": [
        "button[data-testid=\"copy-turn-action-button\"]",
        "button[aria-label=\"Copy response\"]",
        "[data-talvt-turn-state=\"complete\"] [data-markdown-text-style=\"assistant-message\"]"
      ]
    }
  },
  "deepseek-web": {
    "id": "deepseek-web",
    "name": "DeepSeek",
    "url": "https://chat.deepseek.com/",
    "revision": 1,
    "experimental": true,
    "backup": true,
    "capabilities": {
      "text": true,
      "toolProtocol": true,
      "imageInput": false,
      "imageOutput": false,
      "fileTransfer": false,
      "twoWay": false
    },
    "selectors": {
      "hosts": [
        "chat.deepseek.com"
      ],
      "composer": [
        "textarea[placeholder=\"Message DeepSeek\"]",
        "textarea"
      ],
      "send": [
        "[role=\"button\"].ds-button--primary.ds-button--circle",
        "button[aria-label=\"Send\"]",
        "[role=\"button\"][aria-label=\"Send\"]"
      ],
      "responses": [
        ".ds-assistant-message-main-content",
        ".ds-message .ds-markdown"
      ],
      "stop": [
        "button[aria-label=\"Stop\"]",
        "[role=\"button\"][aria-label=\"Stop\"]",
        ".ds-button--primary.ds-button--circle:has(svg rect)"
      ],
      "complete": [
        "[aria-label=\"Read aloud\"]",
        "[aria-label*=\"Copy\"]"
      ],
      "users": [
        ".ds-message:has(.ds-collapsible-text)"
      ],
      "correlation": "ordered-user-message"
    }
  },
  "gemini-web": {
    "id": "gemini-web",
    "name": "Gemini",
    "url": "https://gemini.google.com/app",
    "revision": 2,
    "conversationPath": "^/app/[^/]+/?$",
    "experimental": true,
    "backup": false,
    "capabilities": {
      "text": true,
      "toolProtocol": true,
      "imageInput": false,
      "imageOutput": false,
      "fileTransfer": false,
      "twoWay": false
    },
    "selectors": {
      "hosts": [
        "gemini.google.com"
      ],
      "composer": [
        "rich-textarea [contenteditable=\"true\"]",
        "[contenteditable=\"true\"][role=\"textbox\"]"
      ],
      "send": [
        "button.send-button",
        "button[aria-label=\"Send message\"]"
      ],
      "responses": [
        "model-response .model-response-text",
        "model-response message-content"
      ],
      "stop": [
        "button[aria-label=\"Stop response\"]",
        "button[aria-label=\"Stop generating\"]"
      ],
      "complete": [
        "button[aria-label=\"Copy\"]"
      ],
      "users": ["user-query"],
      "userText": ".query-text-line",
      "busy": ["model-response message-content .markdown[aria-busy=\"true\"]"],
      "completionMarker": [".markdown[aria-busy=\"false\"]"],
      "responseContainer": "model-response",
      "correlation": "ordered-user-message"
    }
  },
  "kimi-web": {
    "id": "kimi-web",
    "name": "Kimi",
    "url": "https://www.kimi.ai/en",
    "revision": 3,
    "conversationPath": "^/chat/(?!history/?$)[^/]+/?$",
    "provisionalConversationPath": "^/chat/p[0-9a-f]{7}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/?$",
    "experimental": true,
    "backup": false,
    "capabilities": {
      "text": true,
      "toolProtocol": true,
      "imageInput": false,
      "imageOutput": false,
      "fileTransfer": false,
      "twoWay": false
    },
    "selectors": {
      "hosts": [
        "www.kimi.ai",
        "www.kimi.com",
        "kimi.com"
      ],
      "composer": [
        ".chat-input-editor[contenteditable=\"true\"]",
        "[contenteditable=\"true\"][role=\"textbox\"]",
        "textarea"
      ],
      "send": [
        ".send-button-container",
        "button[aria-label=\"Send\"]",
        "[data-testid=\"send-button\"]",
        ".send-button"
      ],
      "responses": [
        ".segment-assistant .markdown-container:not(.toolcall-content-text) > .markdown",
        ".segment-assistant .markdown-container:not(.toolcall-content-text)",
        "[data-role=\"assistant\"]"
      ],
      "stop": [
        ".send-button-container.stop",
        ".send-button-container .stop-icon",
        "button[aria-label=\"Stop\"]",
        ".stop-button"
      ],
      "complete": [
        "button[aria-label=\"Read aloud\"]",
        "button[aria-label*=\"Copy\"]",
        ".segment-assistant .copy-button"
      ],
      "accessRequired": ["[data-testid=\"login-phone-input\"]"],
      "users": [".segment-user"],
      "userText": ".user-content__text",
      "toolCodeHeading": "^HARNESS_TOOL_CALL\\s*(?:json)?\\s*(?:Copy)?$",
      "busy": [".send-button-container.loading", ".send-button-container.stop"],
      "errorNotices": ["[data-testid=\"confirm-dialog\"] .body"],
      "responseContainer": ".segment-assistant",
      "correlation": "ordered-user-message"
    }
  }
});})();
