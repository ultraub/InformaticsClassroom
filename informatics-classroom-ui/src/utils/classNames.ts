/**
 * Utility function to combine class names conditionally
 * Similar to the popular `clsx` or `classnames` libraries
 */
export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
