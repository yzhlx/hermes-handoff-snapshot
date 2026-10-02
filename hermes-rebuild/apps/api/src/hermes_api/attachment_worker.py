"""Durable attachment queue worker and isolated parser subprocess entry point."""

import argparse
import json


def _child(args):
    try:
        from .attachment_validation import inspect_file, render_image_preview, render_pdf_page

        if args.inspect:
            result = inspect_file(args.inspect[0], args.inspect[1])
        elif args.render:
            result = render_pdf_page(args.render[0], int(args.render[1]), args.render[2])
        else:
            result = render_image_preview(args.render_image[0], args.render_image[1])
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as error:
        print(json.dumps({"error": getattr(error, "code", "PROCESSING_FAILED")}))
        return 1


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true")
    group.add_argument("--poll-seconds", type=int)
    group.add_argument("--inspect", nargs=2, metavar=("PATH", "MIME"))
    group.add_argument("--render", nargs=3, metavar=("PATH", "PAGE", "OUTPUT"))
    group.add_argument("--render-image", nargs=2, metavar=("PATH", "OUTPUT"))
    args = parser.parse_args()
    if args.inspect or args.render or args.render_image:
        return _child(args)
    if args.poll_seconds is not None and not 1 <= args.poll_seconds <= 60:
        parser.error("poll interval must be 1..60 seconds")
    import time

    from sqlalchemy.orm import Session

    from .attachment_object_store import make_store
    from .attachment_repository import SQLAttachmentRepository
    from .attachment_service import AttachmentService
    from .attachment_validation import ProcessFileValidator
    from .settings import Settings
    from .storage import make_engine

    config = Settings()
    engine, store = make_engine(config.database_url), make_store(config)
    interval = args.poll_seconds
    try:
        while True:
            with Session(engine) as db:
                repository = SQLAttachmentRepository(db, store, ProcessFileValidator())
                did_work = AttachmentService(repository).run_one()
            if interval is None:
                return 0
            if not did_work:
                time.sleep(interval)
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
