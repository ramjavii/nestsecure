'use client';

import { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SearchInputProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
  className?: string;
}

export function SearchInput({
  value: externalValue,
  onChange,
  placeholder = 'Buscar...',
  debounceMs = 300,
  className,
}: SearchInputProps) {
  const [internalValue, setInternalValue] = useState(externalValue || '');

  // Sync external value
  useEffect(() => {
    if (externalValue !== undefined) {
      setInternalValue(externalValue);
    }
  }, [externalValue]);

  // Debounce the onChange callback
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(internalValue);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [internalValue, debounceMs, onChange]);

  const handleClear = () => {
    setInternalValue('');
    onChange('');
  };

  return (
    <div className={cn('relative', className)}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="search"
        value={internalValue}
        onChange={(e) => setInternalValue(e.target.value)}
        placeholder={placeholder}
        className="pl-9 pr-8"
      />
      {internalValue && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
          onClick={handleClear}
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
