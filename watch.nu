#!/usr/bin/env nu
# Watches restart.txt and rebuilds dev and/or prod environments in parallel.
# Runs on the HOST SERVER (has podman access). Not usable from Claude Code's container.
# Usage: nu watch.nu [--dev] [--prod]  (default: both)

def main [
    --dev   # Watch and rebuild dev only
    --prod  # Watch and rebuild prod only
] {
    let root = ($env.FILE_PWD? | default ($env.CURRENT_FILE | path dirname))

    let build_dev  = ($root | path join "build.dev.log")
    let build_prod = ($root | path join "build.prod.log")
    let watch_file = ($root | path join "restart.txt")

    let do_dev  = ($dev  or (not $dev and not $prod))
    let do_prod = ($prod or (not $dev and not $prod))

    print $"Watching ($watch_file) for changes..."
    print $"  dev:  ($do_dev)  → ($build_dev)"
    print $"  prod: ($do_prod) → ($build_prod)"
    print "Press Ctrl-C to stop."

    watch $watch_file {|op, path|
        print $"\n[($env.CURRENT_FILE | path basename)] restart.txt changed \(($op)\) — rebuilding..."

        if $do_dev {
            job spawn {
                print "[dev] Starting rebuild..."
                ^podman compose up -d --force-recreate --build out+err> $build_dev
                print "[dev] Done."
            }
        }

        if $do_prod {
            job spawn {
                print "[prod] Starting rebuild..."
                ^podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build out+err> $build_prod
                print "[prod] Done."
            }
        }
    }
}
