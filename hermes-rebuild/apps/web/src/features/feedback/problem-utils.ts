import type { components } from '../../../../../packages/contracts/src/schema';
import { errorCategoryLabels } from '../../shared/ui/labels';

export type ResultValue = components['schemas']['Result'];
export type ErrorCategory = components['schemas']['ErrorCategory'];

export const operationId = () => crypto.randomUUID();
export const optionalText = (value: string) => value.trim() || null;
export const errorOptions = Object.entries(errorCategoryLabels) as [ErrorCategory, string][];
