import { ReactNode } from 'react';
import { classNames } from '../../utils/classNames';

export interface CardProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  headerAction?: ReactNode;
  footer?: ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  className?: string;
}

export function Card({
  children,
  title,
  subtitle,
  headerAction,
  footer,
  padding = 'md',
  hover = false,
  className,
}: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  return (
    <div
      className={classNames(
        'bg-white rounded-lg shadow-sm border border-gray-200',
        hover && 'transition-shadow hover:shadow-md',
        className
      )}
    >
      {(title || subtitle || headerAction) && (
        <div
          className={classNames(
            'border-b border-gray-200',
            paddingClasses[padding]
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-medium text-gray-900">{title}</h3>
              )}
              {subtitle && (
                <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
              )}
            </div>
            {headerAction && <div>{headerAction}</div>}
          </div>
        </div>
      )}
      <div className={paddingClasses[padding]}>{children}</div>
      {footer && (
        <div
          className={classNames(
            'border-t border-gray-200 bg-gray-50',
            paddingClasses[padding]
          )}
        >
          {footer}
        </div>
      )}
    </div>
  );
}
