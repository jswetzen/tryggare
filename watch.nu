#!/usr/bin/env nu
# Watches restart-dev.txt / restart-prod.txt and rebuilds the matching
# environment only. Two separate trigger files (not a shared restart.txt) so
# that routine dev iteration never also kicks off the slower prod-like
# rebuild — prod is only meant to be restarted for final/human verification,
# not on every dev change. See CLAUDE.md's Deployment Environments section.
# Runs on the HOST SERVER (has podman access). Not usable from Claude Code's container.
# Usage: nu watch.nu [--dev] [--prod]  (default: both, in this one process)

def main [
    --dev   # Watch and rebuild dev only
    --prod  # Watch and rebuild prod only
] {
    let root = ($env.FILE_PWD? | default ($env.CURRENT_FILE | path dirname))
    let do_dev  = ($dev  or (not $dev and not $prod))
    let do_prod = ($prod or (not $dev and not $prod))

    # restart-*.txt is gitignored — a fresh clone won't have them yet, and a
    # trigger that doesn't exist can never fire. Touch the ones we watch.
    let triggers = ([
        (if $do_dev  { "restart-dev.txt" })
        (if $do_prod { "restart-prod.txt" })
    ] | compact)
    for t in $triggers {
        let p = ($root | path join $t)
        if not ($p | path exists) { "" | save $p }
    }

    print $"Watching ($root) for changes to:"
    if $do_dev  { print $"  restart-dev.txt  → dev  rebuild, log: ($root | path join 'build.dev.log')" }
    if $do_prod { print $"  restart-prod.txt → prod rebuild, log: ($root | path join 'build.prod.log')" }
    print "Press Ctrl-C to stop."

    # One `watch` on the directory rather than one per file: `watch` blocks, so
    # watching two files used to mean a second background process, whose output
    # was swallowed (it looked like only dev was being watched) and which could
    # be orphaned if this process died without a clean Ctrl-C. Watching the
    # directory non-recursively with a glob keeps both triggers in this single
    # foreground process — one Ctrl-C stops everything, and both streams print
    # here under [dev]/[prod] prefixes.
    #
    # --recursive false matters: the repo root contains node_modules/, .git/ and
    # frontend/, and a recursive watch would be both slow and liable to exhaust
    # inotify watches. The glob is also re-checked per event below, since a
    # single `echo > file` can surface as several ops (Write, Chmod, ...);
    # --debounce coalesces those into one rebuild.
    watch $root --glob "restart-*.txt" --recursive false --debounce 500ms {|op, path|
        let name = ($path | path basename)
        if $do_dev and $name == "restart-dev.txt" {
            rebuild_dev $root $op
        } else if $do_prod and $name == "restart-prod.txt" {
            rebuild_prod $root $op
        }
    }
}

def rebuild_dev [root: string, op: string] {
    let build_dev = ($root | path join "build.dev.log")
    print $"\n[dev] restart-dev.txt changed \(($op)\) — rebuilding..."
    # Spawned so a long rebuild doesn't block the watcher from noticing the
    # other environment's trigger. Dev and prod are separate compose projects
    # (tryggare_* on 8000/5173 vs check-in-prod_* on 8080) with distinct image
    # and container names, so an overlapping dev+prod rebuild doesn't collide.
    job spawn {
        print "[dev] Starting rebuild..."
        ^podman compose up -d --force-recreate --build out+err> $build_dev
        print "[dev] Done."
    } | ignore
}

def rebuild_prod [root: string, op: string] {
    let build_prod = ($root | path join "build.prod.log")
    print $"\n[prod] restart-prod.txt changed \(($op)\) — rebuilding..."
    job spawn {
        print "[prod] Starting rebuild..."
        # The prod compose declares an external 'traefik' network; ensure it
        # exists first or `up` aborts before building (truncates the log).
        ^bash ($root | path join "scripts" "ensure-prod-network.sh") out+err> $build_prod
        ^podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build out+err>> $build_prod
        print "[prod] Done."
    } | ignore
}
