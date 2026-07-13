#!/usr/bin/env nu
# Watches restart-dev.txt / restart-prod.txt independently and rebuilds the
# matching environment only. Two separate trigger files (not a shared
# restart.txt) so that routine dev iteration never also kicks off the
# slower prod-like rebuild — prod is only meant to be restarted for final/
# human verification, not on every dev change. See CLAUDE.md's Deployment
# Environments section.
# Runs on the HOST SERVER (has podman access). Not usable from Claude Code's container.
# Usage: nu watch.nu [--dev] [--prod]  (default: both, as two independent watchers)

def main [
    --dev   # Watch and rebuild dev only
    --prod  # Watch and rebuild prod only
] {
    let root = ($env.FILE_PWD? | default ($env.CURRENT_FILE | path dirname))
    let do_dev  = ($dev  or (not $dev and not $prod))
    let do_prod = ($prod or (not $dev and not $prod))

    if $do_dev and $do_prod {
        # watch() blocks, so a single process can't watch two independent
        # files at once — re-exec this same script as a background process
        # for prod and keep dev in the foreground to hold the process open.
        job spawn { ^nu $env.CURRENT_FILE --prod } | ignore
        watch_dev $root
    } else if $do_dev {
        watch_dev $root
    } else if $do_prod {
        watch_prod $root
    }
}

def watch_dev [root: string] {
    let build_dev = ($root | path join "build.dev.log")
    let trigger = ($root | path join "restart-dev.txt")
    print $"Watching ($trigger) for changes..."
    print $"  dev → ($build_dev)"
    print "Press Ctrl-C to stop."

    watch $trigger {|op, path|
        print $"\n[dev] restart-dev.txt changed \(($op)\) — rebuilding..."
        job spawn {
            print "[dev] Starting rebuild..."
            ^podman compose up -d --force-recreate --build out+err> $build_dev
            print "[dev] Done."
        } | ignore
    }
}

def watch_prod [root: string] {
    let build_prod = ($root | path join "build.prod.log")
    let trigger = ($root | path join "restart-prod.txt")
    print $"Watching ($trigger) for changes..."
    print $"  prod → ($build_prod)"
    print "Press Ctrl-C to stop."

    watch $trigger {|op, path|
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
}
