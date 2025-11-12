/**
 * Feature Flags
 *
 * This module provides type-safe feature flag checks.
 * Feature flags allow enabling/disabling features via environment variables.
 */

/**
 * Check if printer integration is enabled
 * When false, QR codes are displayed on screen instead of printing
 */
export function isPrinterEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FEATURE_PRINTER_ENABLED === "true";
}

/**
 * Check if full admin CRUD is enabled
 * When false, admins can only be created via seed script
 */
export function isAdminCrudEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FEATURE_ADMIN_FULL_CRUD !== "false";
}

/**
 * Check if QR code generation is enabled
 * When false, no QR codes are generated for children
 */
export function isQrCodeEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FEATURE_QR_CODE_ENABLED !== "false";
}

/**
 * Check if audit log UI is enabled
 * When false, audit logs are still recorded but not visible in UI
 */
export function isAuditLogUiEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FEATURE_AUDIT_LOG_UI !== "false";
}

/**
 * Get all feature flags as an object
 */
export function getAllFeatures() {
  return {
    printerEnabled: isPrinterEnabled(),
    adminCrudEnabled: isAdminCrudEnabled(),
    qrCodeEnabled: isQrCodeEnabled(),
    auditLogUiEnabled: isAuditLogUiEnabled(),
  };
}
