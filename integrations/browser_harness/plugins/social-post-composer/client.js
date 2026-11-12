window.__ModuleLoader__.load({
  id: '@local/social-post-composer',
  factory(require) {
    const React = require('react');
    const h = React.createElement;

    // Per-network publishing limits (characters).
    const NETWORKS = [
      { id: 'x', label: 'X / Twitter', limit: 280 },
      { id: 'linkedin', label: 'LinkedIn', limit: 3000 },
    ];

    function shareUrl(network, text) {
      const encoded = encodeURIComponent(text);
      if (network.id === 'x') {
        return 'https://x.com/intent/post?text=' + encoded;
      }
      // LinkedIn has no reliable web intent for a prefilled post; open the feed.
      return 'https://www.linkedin.com/feed/?shareActive=true';
    }

    function Panel() {
      const [open, setOpen] = React.useState(false);
      const [text, setText] = React.useState('');
      const [copied, setCopied] = React.useState(false);
      const [failed, setFailed] = React.useState(false);

      const count = Array.from(text).length;

      const toggle = () => {
        setOpen((v) => !v);
        setCopied(false);
        setFailed(false);
      };

      const copy = async () => {
        if (!text) return;
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setFailed(false);
        } catch (error) {
          setCopied(false);
          setFailed(true);
        }
      };

      const clear = () => {
        setText('');
        setCopied(false);
        setFailed(false);
      };

      const trigger = h('button', {
        type: 'button',
        onClick: toggle,
        title: open ? 'Close the social post composer' : 'Compose a social post',
        'aria-expanded': open,
        style: {
          display: 'inline-flex', alignSelf: 'flex-start', alignItems: 'center',
          gap: 6, padding: '4px 10px', borderRadius: 999, cursor: 'pointer',
          fontSize: 12, lineHeight: '18px',
          border: '1px solid var(--dsh-border, rgba(127,127,127,0.35))',
          background: 'transparent',
          color: 'var(--dsh-text-secondary, inherit)',
        },
      }, h('span', { 'aria-hidden': true }, '\u2709'), 'Social post');

      const body = !open ? null : h('div', {
        style: {
          marginTop: 8, padding: 10, borderRadius: 12,
          border: '1px solid var(--dsh-border, rgba(127,127,127,0.35))',
          background: 'var(--dsh-surface, transparent)',
          display: 'flex', flexDirection: 'column', gap: 8,
        },
      },
        h('textarea', {
          value: text,
          onChange: (e) => { setText(e.target.value); setCopied(false); },
          placeholder: 'Write the post you want to publish\u2026',
          rows: 4,
          style: {
            width: '100%', resize: 'vertical', boxSizing: 'border-box',
            padding: 8, borderRadius: 8, fontSize: 13, lineHeight: '20px',
            border: '1px solid var(--dsh-border, rgba(127,127,127,0.35))',
            background: 'transparent', color: 'inherit', font: 'inherit',
          },
        }),
        h('div', {
          style: { display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 12 },
        }, NETWORKS.map((network) => {
          const remaining = network.limit - count;
          const over = remaining < 0;
          return h('span', {
            key: network.id,
            title: over
              ? String(-remaining) + ' characters over the ' + network.label + ' limit'
              : String(remaining) + ' left on ' + network.label,
            style: { color: over ? '#d93025' : 'inherit', opacity: over ? 1 : 0.7 },
          }, network.label + ' ' + count + '/' + network.limit);
        })),
        h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' } },
          h('button', {
            type: 'button', onClick: copy, disabled: !text,
            style: buttonStyle(!text),
          }, copied ? 'Copied' : 'Copy text'),
          h('button', {
            type: 'button', onClick: clear, disabled: !text,
            style: buttonStyle(!text),
          }, 'Clear'),
          NETWORKS.map((network) => h('a', {
            key: network.id,
            href: shareUrl(network, text),
            target: '_blank',
            rel: 'noopener noreferrer',
            style: { ...buttonStyle(!text), textDecoration: 'none', pointerEvents: text ? 'auto' : 'none', opacity: text ? 1 : 0.5 },
          }, 'Open on ' + network.label)),
        ),
        failed
          ? h('div', { style: { fontSize: 12, color: '#d93025' } }, 'Copy failed \u2014 select the text and copy it manually')
          : null,
      );

      return h('div', {
        style: { display: 'flex', flexDirection: 'column', width: '100%', boxSizing: 'border-box' },
      }, trigger, body);
    }

    function buttonStyle(disabled) {
      return {
        padding: '3px 9px', borderRadius: 8, cursor: disabled ? 'default' : 'pointer',
        fontSize: 12, lineHeight: '18px',
        border: '1px solid var(--dsh-border, rgba(127,127,127,0.35))',
        background: 'transparent', color: 'inherit', font: 'inherit',
        opacity: disabled ? 0.5 : 1,
      };
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('conversation.composer.dock', () => ctx.slots.register({
          name: 'conversation.composer.dock',
          id: 'social-post-composer',
          order: 5,
        }, Panel));
      },
    };
  },
});
