/**
 * What the signed-in user may do, and the one thing `is_staff` still means.
 *
 * `is_staff` used to carry two unrelated jobs: "can open Django admin" and "is
 * a privileged app user". Every app-tier decision now reads `permissions`
 * instead — the `"app_label.codename"` strings the backend itself checks
 * (`accounts/views.py::session_user_payload`). Because they are the same
 * strings on both sides, moving a permission between roles in Django admin
 * needs no change here at all.
 *
 * Gate on permissions, never on `roles`. An organisation can compose a fourth
 * group in Django admin, and its name is one this frontend has never heard of;
 * `roles` exists for display ("you are signed in as…") and nothing else.
 *
 * A superuser's payload already contains every permission, so no branch here
 * needs to special-case `is_superuser`.
 */

export interface SessionUser {
  id: string;
  username: string;
  name: string;
  /** Only ever means "can open /admin/". Nothing else may branch on it. */
  is_staff: boolean;
  is_superuser: boolean;
  /** Group names, for display only. */
  roles: string[];
  /** Sorted `app_label.codename` strings. This is what to gate on. */
  permissions: string[];
}

/**
 * The permission strings this frontend gates on, named by what they open.
 *
 * Keeping them in one place means the codename appears once, next to the
 * reason it is being asked for, rather than as a bare string scattered through
 * route guards.
 */
export const PERMISSION = {
  /** Opens /reports — the aggregate financial and attendance picture. */
  viewReports: 'reports.view_eventreport',
  /**
   * Builds a new report snapshot. Strictly more than `viewReports`: a
   * Koordinator holds both, a role granted only the read does not, and the
   * page must not offer a button that is going to 403.
   */
  addReports: 'reports.add_eventreport',
  /** Opens /import — configuring and running a booking-system import. */
  viewImportSources: 'imports.view_importsource',
  /** Edit a child's record, including the allergy/medical text. */
  changeChild: 'families.change_child',
  /** Edit a parent's record. Adults carry health fields too. */
  changeParent: 'families.change_parent'
} as const;

export type PermissionString = (typeof PERMISSION)[keyof typeof PERMISSION];

/** True when `user` holds `permission`. Anonymous/unknown users hold nothing. */
export function hasPermission(
  user: Pick<SessionUser, 'permissions'> | null | undefined,
  permission: string
): boolean {
  return Boolean(user?.permissions?.includes(permission));
}

/**
 * Whether this user may edit health fields on the check-in screen's inline
 * family edit — and therefore sees the allergy text without revealing it.
 *
 * Both codenames, not either: the panel edits parents and children in one
 * atomic call, so a user who could only change one of the two would submit a
 * form that fails as a whole. The seeded roles grant them together.
 */
export function canEditFamilyHealthInfo(
  user: Pick<SessionUser, 'permissions'> | null | undefined
): boolean {
  return (
    hasPermission(user, PERMISSION.changeChild) &&
    hasPermission(user, PERMISSION.changeParent)
  );
}
