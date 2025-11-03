import { useEffect, useState } from 'react';

/**
 * Custom hook for keyboard shortcuts
 * @param {Object} callbacks - Object with callback functions
 * @param {Function} callbacks.onStartStopRecording - Ctrl/Cmd + R
 * @param {Function} callbacks.onSave - Ctrl/Cmd + S
 * @param {Function} callbacks.onExport - Ctrl/Cmd + E
 * @param {Function} callbacks.onSendToDentrix - Ctrl/Cmd + D
 * @param {Function} callbacks.onFocusSearch - Ctrl/Cmd + K
 * @param {Function} callbacks.onCancel - Escape
 * @param {Function} callbacks.onShowHelp - ?
 */
const useKeyboardShortcuts = (callbacks = {}) => {
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event) => {
      // Check for Ctrl (Windows/Linux) or Cmd (Mac)
      const isMod = event.ctrlKey || event.metaKey;

      // Ctrl/Cmd + R: Start/stop recording
      if (isMod && event.key === 'r') {
        event.preventDefault();
        callbacks.onStartStopRecording?.();
      }

      // Ctrl/Cmd + S: Save session
      else if (isMod && event.key === 's') {
        event.preventDefault();
        callbacks.onSave?.();
      }

      // Ctrl/Cmd + E: Export to PDF
      else if (isMod && event.key === 'e') {
        event.preventDefault();
        callbacks.onExport?.();
      }

      // Ctrl/Cmd + D: Send to Dentrix
      else if (isMod && event.key === 'd') {
        event.preventDefault();
        callbacks.onSendToDentrix?.();
      }

      // Ctrl/Cmd + K: Focus search
      else if (isMod && event.key === 'k') {
        event.preventDefault();
        callbacks.onFocusSearch?.();
      }

      // Escape: Cancel current action
      else if (event.key === 'Escape') {
        event.preventDefault();
        callbacks.onCancel?.();
      }

      // ?: Show shortcuts help
      else if (event.key === '?' && !isMod && !event.shiftKey) {
        event.preventDefault();
        setShowShortcutsHelp(true);
        callbacks.onShowHelp?.();
      }
    };

    // Add event listener
    window.addEventListener('keydown', handleKeyDown);

    // Cleanup
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [callbacks]);

  const shortcuts = [
    {
      keys: ['Ctrl', 'R'],
      macKeys: ['⌘', 'R'],
      description: 'Start/stop recording',
      action: 'onStartStopRecording'
    },
    {
      keys: ['Ctrl', 'S'],
      macKeys: ['⌘', 'S'],
      description: 'Save session',
      action: 'onSave'
    },
    {
      keys: ['Ctrl', 'E'],
      macKeys: ['⌘', 'E'],
      description: 'Export to PDF',
      action: 'onExport'
    },
    {
      keys: ['Ctrl', 'D'],
      macKeys: ['⌘', 'D'],
      description: 'Send to Dentrix',
      action: 'onSendToDentrix'
    },
    {
      keys: ['Ctrl', 'K'],
      macKeys: ['⌘', 'K'],
      description: 'Focus search',
      action: 'onFocusSearch'
    },
    {
      keys: ['Esc'],
      macKeys: ['Esc'],
      description: 'Cancel current action',
      action: 'onCancel'
    },
    {
      keys: ['?'],
      macKeys: ['?'],
      description: 'Show shortcuts help',
      action: 'onShowHelp'
    }
  ];

  return {
    shortcuts,
    showShortcutsHelp,
    setShowShortcutsHelp
  };
};

/**
 * Keyboard shortcut hint component
 * @param {Array} keys - Array of key names to display
 */
export const KeyboardShortcut = ({ keys }) => {
  // Detect if user is on Mac
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  
  return (
    <span className="inline-flex gap-1">
      {keys.map((key, index) => (
        <kbd
          key={index}
          className="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-300 rounded shadow"
        >
          {isMac && key === 'Ctrl' ? '⌘' : key}
        </kbd>
      ))}
    </span>
  );
};

/**
 * Shortcuts help modal component
 * @param {Array} shortcuts - Array of shortcut objects
 * @param {Function} onClose - Close callback
 */
export const ShortcutsHelpModal = ({ shortcuts, onClose }) => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-800">Keyboard Shortcuts</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
            >
              ×
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            Use these shortcuts to navigate faster
          </p>
        </div>

        <div className="p-6">
          <div className="space-y-3">
            {shortcuts.map((shortcut, index) => (
              <div
                key={index}
                className="flex justify-between items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <span className="text-gray-700">{shortcut.description}</span>
                <div className="flex gap-1">
                  {(isMac ? shortcut.macKeys : shortcut.keys).map((key, keyIndex) => (
                    <kbd
                      key={keyIndex}
                      className="px-3 py-1.5 text-sm font-semibold text-gray-800 bg-white border border-gray-300 rounded shadow"
                    >
                      {key}
                    </kbd>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Tip:</strong> Press <kbd className="px-2 py-1 text-xs bg-white border border-blue-300 rounded">?</kbd> anytime to see this help dialog
            </p>
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Got it!
          </button>
        </div>
      </div>
    </div>
  );
};

export default useKeyboardShortcuts;
