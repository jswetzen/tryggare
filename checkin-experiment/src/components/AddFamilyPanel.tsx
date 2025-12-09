import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import type { TicketType } from '../types';

interface AddFamilyPanelProps {
  onAdd: (data: {
    familyName: string;
    childrenNames: string[];
    ticketType: TicketType;
  }) => void;
  onClose: () => void;
}

/**
 * AddFamilyPanel component
 *
 * Expands between session bar and search to add families with children.
 * Allows setting a default ticket type for all children in the family.
 */
export function AddFamilyPanel({ onAdd, onClose }: AddFamilyPanelProps) {
  const [familyName, setFamilyName] = useState('');
  const [childrenNames, setChildrenNames] = useState(['']);
  const [ticketType, setTicketType] = useState<TicketType>('none');
  const [error, setError] = useState('');
  const familyNameInputRef = useRef<HTMLInputElement>(null);

  // Focus family name input on mount
  useEffect(() => {
    familyNameInputRef.current?.focus();
  }, []);

  // Handle Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleAddChild = () => {
    setChildrenNames([...childrenNames, '']);
  };

  const handleRemoveChild = (index: number) => {
    setChildrenNames(childrenNames.filter((_, i) => i !== index));
  };

  const handleChildNameChange = (index: number, value: string) => {
    const newNames = [...childrenNames];
    newNames[index] = value;
    setChildrenNames(newNames);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate family name
    if (!familyName.trim()) {
      setError('Family name is required');
      return;
    }

    // Filter out empty child names and validate
    const validChildren = childrenNames
      .map((name) => name.trim())
      .filter((name) => name.length > 0);

    if (validChildren.length === 0) {
      setError('At least one child name is required');
      return;
    }

    // Submit
    onAdd({
      familyName: familyName.trim(),
      childrenNames: validChildren,
      ticketType,
    });
  };

  return (
    <div
      className="bg-white border border-slate-300 rounded-lg p-4 mb-4 shadow-sm"
      data-testid="add-family-panel"
    >
      <form onSubmit={handleSubmit}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">Add New Family</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-600 transition-colors"
            data-testid="add-family-close-button"
          >
            <X size={20} />
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Family Name */}
        <div className="mb-4">
          <label
            htmlFor="family-name"
            className="block text-sm font-semibold text-slate-700 mb-1"
          >
            Family Name:
          </label>
          <input
            ref={familyNameInputRef}
            id="family-name"
            type="text"
            value={familyName}
            onChange={(e) => setFamilyName(e.target.value)}
            placeholder="Garcia, Smith, etc."
            className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="add-family-name-input"
          />
        </div>

        {/* Ticket Type Selector */}
        <div className="mb-4">
          <label
            htmlFor="ticket-type"
            className="block text-sm font-semibold text-slate-700 mb-1"
          >
            Ticket:
          </label>
          <select
            id="ticket-type"
            value={ticketType}
            onChange={(e) => setTicketType(e.target.value as TicketType)}
            className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="none">No Ticket</option>
            <option value="session">Session Only</option>
            <option value="event">Full Event Pass</option>
          </select>
        </div>

        {/* Children */}
        <div className="mb-4">
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Children:
          </label>
          <div className="space-y-2">
            {childrenNames.map((name, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => handleChildNameChange(index, e.target.value)}
                  placeholder={`Child ${index + 1} name`}
                  className="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {index > 0 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveChild(index)}
                    aria-label="Remove child"
                    className="text-red-600 hover:text-red-700 text-sm font-medium px-2 py-1"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={handleAddChild}
            className="mt-2 text-blue-600 hover:text-blue-700 text-sm font-semibold"
          >
            + Add Child
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-300 transition-colors"
            data-testid="add-family-cancel-button"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            data-testid="add-family-submit-button"
          >
            Add Family
          </button>
        </div>
      </form>
    </div>
  );
}
