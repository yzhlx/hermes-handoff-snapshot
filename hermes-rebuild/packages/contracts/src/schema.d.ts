export interface paths {
    "/api/v1/account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Status */
        get: operations["status_api_v1_account_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/deletion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Deletion */
        post: operations["request_deletion_api_v1_account_deletion_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/deletion/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Deletion */
        post: operations["cancel_deletion_api_v1_account_deletion_cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/deletion/purge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Purge Deletion */
        post: operations["purge_deletion_api_v1_account_deletion_purge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Exports */
        get: operations["list_exports_api_v1_account_exports_get"];
        put?: never;
        /** Create Export */
        post: operations["create_export_api_v1_account_exports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/exports/{export_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download Export */
        get: operations["download_export_api_v1_account_exports__export_id__download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/advisor/analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items_api_v1_advisor_analyses_get"];
        put?: never;
        /** Create */
        post: operations["create_api_v1_advisor_analyses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/advisor/analyses/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get */
        get: operations["get_api_v1_advisor_analyses__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/advisor/analyses/{run_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel */
        post: operations["cancel_api_v1_advisor_analyses__run_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/{attachment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Attachment */
        get: operations["get_attachment_api_v1_attachments__attachment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/{attachment_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete_api_v1_attachments__attachment_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/{attachment_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Content */
        get: operations["content_api_v1_attachments__attachment_id__content_get"];
        /** Upload */
        put: operations["upload_api_v1_attachments__attachment_id__content_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/{attachment_id}/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview Job */
        post: operations["preview_job_api_v1_attachments__attachment_id__jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/{attachment_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview */
        get: operations["preview_api_v1_attachments__attachment_id__preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attachments/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Initialize */
        post: operations["initialize_api_v1_attachments_uploads_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Session */
        get: operations["session_api_v1_auth_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/chapters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Chapters */
        get: operations["chapters_api_v1_chapters_get"];
        put?: never;
        /** Create Chapter */
        post: operations["create_chapter_api_v1_chapters_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/chapters/{chapter_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Chapter */
        get: operations["chapter_api_v1_chapters__chapter_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Chapter */
        patch: operations["patch_chapter_api_v1_chapters__chapter_id__patch"];
        trace?: never;
    };
    "/api/v1/day-summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Day Summary */
        get: operations["day_summary_api_v1_day_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Live */
        get: operations["live_api_v1_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["ready_api_v1_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/home": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Home */
        get: operations["get_home_api_v1_home_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job_api_v1_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/knowledge-points": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Points */
        get: operations["points_api_v1_knowledge_points_get"];
        put?: never;
        /** Create Point */
        post: operations["create_point_api_v1_knowledge_points_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/knowledge-points/{knowledge_point_id}/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Knowledge Point Evidence */
        get: operations["knowledge_point_evidence_api_v1_knowledge_points__knowledge_point_id__evidence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/knowledge-points/{point_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Point */
        get: operations["point_api_v1_knowledge_points__point_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Point */
        patch: operations["patch_point_api_v1_knowledge_points__point_id__patch"];
        trace?: never;
    };
    "/api/v1/learning-methods": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Learning Methods */
        get: operations["learning_methods_api_v1_learning_methods_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-methods/{method_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Learning Method */
        get: operations["learning_method_api_v1_learning_methods__method_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Session History */
        get: operations["session_history_api_v1_learning_sessions_get"];
        put?: never;
        /** Start */
        post: operations["start_api_v1_learning_sessions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Session Detail */
        get: operations["session_detail_api_v1_learning_sessions__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Learning Session */
        post: operations["cancel_learning_session_api_v1_learning_sessions__session_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}/end": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** End */
        post: operations["end_api_v1_learning_sessions__session_id__end_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pause Learning Session */
        post: operations["pause_learning_session_api_v1_learning_sessions__session_id__pause_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resume Learning Session */
        post: operations["resume_learning_session_api_v1_learning_sessions__session_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Correct Time Segment */
        patch: operations["correct_time_segment_api_v1_learning_sessions__session_id__time_segments__segment_id__patch"];
        trace?: never;
    };
    "/api/v1/learning-sessions/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current */
        get: operations["current_api_v1_learning_sessions_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-situations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Learning Situations */
        get: operations["learning_situations_api_v1_learning_situations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learning-situations/{situation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Learning Situation */
        get: operations["learning_situation_api_v1_learning_situations__situation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/mastery-assessments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Mastery Assessment */
        post: operations["create_mastery_assessment_api_v1_mastery_assessments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/meta": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Metadata */
        get: operations["metadata_api_v1_meta_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problem-attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Attempt */
        post: operations["create_attempt_api_v1_problem_attempts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problem-attempts/{attempt_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Attempt */
        get: operations["attempt_api_v1_problem_attempts__attempt_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Attempt */
        patch: operations["update_attempt_api_v1_problem_attempts__attempt_id__patch"];
        trace?: never;
    };
    "/api/v1/problem-comparisons": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items_api_v1_problem_comparisons_get"];
        put?: never;
        /** Create */
        post: operations["create_api_v1_problem_comparisons_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problem-comparisons/{comparison_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get */
        get: operations["get_api_v1_problem_comparisons__comparison_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch */
        patch: operations["patch_api_v1_problem_comparisons__comparison_id__patch"];
        trace?: never;
    };
    "/api/v1/problems": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Problems */
        get: operations["problems_api_v1_problems_get"];
        put?: never;
        /** Create Problem */
        post: operations["create_problem_api_v1_problems_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problems/{problem_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Problem */
        get: operations["problem_api_v1_problems__problem_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Problem */
        patch: operations["update_problem_api_v1_problems__problem_id__patch"];
        trace?: never;
    };
    "/api/v1/problems/{problem_id}/attachment-links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Problem Attachment Links */
        get: operations["problem_attachment_links_api_v1_problems__problem_id__attachment_links_get"];
        put?: never;
        /** Link Problem Attachment */
        post: operations["link_problem_attachment_api_v1_problems__problem_id__attachment_links_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problems/{problem_id}/attachment-links/{link_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Unlink Problem Attachment */
        delete: operations["unlink_problem_attachment_api_v1_problems__problem_id__attachment_links__link_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/problems/{problem_id}/knowledge-links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Link Problem */
        put: operations["link_problem_api_v1_problems__problem_id__knowledge_links_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quotes/{quote_id}/preference": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Preference */
        put: operations["update_preference_api_v1_quotes__quote_id__preference_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quotes/favorites": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Favorites */
        get: operations["favorites_api_v1_quotes_favorites_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quotes/today": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Today */
        get: operations["today_api_v1_quotes_today_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/records": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Records */
        get: operations["records_api_v1_records_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/session-reflections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Reflection */
        post: operations["create_reflection_api_v1_session_reflections_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/session-reflections/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reflection */
        get: operations["reflection_api_v1_session_reflections__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Reflection */
        patch: operations["update_reflection_api_v1_session_reflections__session_id__patch"];
        trace?: never;
    };
    "/api/v1/stuck-points": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items_api_v1_stuck_points_get"];
        put?: never;
        /** Create */
        post: operations["create_api_v1_stuck_points_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stuck-points/{stuck_point_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get */
        get: operations["get_api_v1_stuck_points__stuck_point_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch */
        patch: operations["patch_api_v1_stuck_points__stuck_point_id__patch"];
        trace?: never;
    };
    "/api/v1/subjects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Subjects */
        get: operations["subjects_api_v1_subjects_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/subjects/{subject_id}/space": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Subject Space */
        get: operations["subject_space_api_v1_subjects__subject_id__space_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Suggestions */
        get: operations["suggestions_api_v1_suggestions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suggestions/{suggestion_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Suggestion */
        get: operations["suggestion_api_v1_suggestions__suggestion_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suggestions/{suggestion_id}/actions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Action */
        post: operations["action_api_v1_suggestions__suggestion_id__actions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountDeletionData */
        AccountDeletionData: {
            /** Cancelled At */
            cancelled_at: string | null;
            /** Completed At */
            completed_at: string | null;
            /** Confirmation */
            confirmation: string;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Impact */
            impact: {
                [key: string]: unknown;
            };
            /** Purge After */
            purge_after: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "cancelled" | "completed";
            /** Version */
            version: number;
        };
        /** AccountExportData */
        AccountExportData: {
            /** Byte Size */
            byte_size: number | null;
            /** Created At */
            created_at: string;
            /** Expires At */
            expires_at: string | null;
            /** Id */
            id: string;
            /** Record Counts */
            record_counts: {
                [key: string]: unknown;
            };
            /** Sha256 */
            sha256: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "failed" | "expired";
        };
        /** AccountExportPageData */
        AccountExportPageData: {
            /** Items */
            items: components["schemas"]["AccountExportData"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** AccountStatusData */
        AccountStatusData: {
            deletion: components["schemas"]["AccountDeletionData"] | null;
            /** Record Count */
            record_count: number;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deletion_pending" | "deleted";
            /** Timezone */
            timezone: string;
            /** Username */
            username: string;
        };
        /** AdvisorPageData */
        AdvisorPageData: {
            /** Items */
            items: components["schemas"]["AdvisorRunData"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** AdvisorPrivacy */
        AdvisorPrivacy: {
            /** External */
            external: boolean;
            /** Provider */
            provider: string;
            /** Scope */
            scope: string;
        };
        /** AdvisorRunData */
        AdvisorRunData: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Data Version */
            data_version: string;
            /** Degradation Reason */
            degradation_reason: string | null;
            /** Evidence Count */
            evidence_count: number;
            /** Evidence Refs */
            evidence_refs: components["schemas"]["EvidenceRef"][];
            /** Facts */
            facts: components["schemas"]["CitedText"][];
            /** Id */
            id: string;
            /** Inferences */
            inferences: components["schemas"]["CitedText"][];
            /** Knowledge Point Id */
            knowledge_point_id: string | null;
            /** Missing Information */
            missing_information: string[];
            /** Model Id */
            model_id: string;
            /** Policy Version */
            policy_version: string;
            privacy: components["schemas"]["AdvisorPrivacy"];
            /** Prompt Version */
            prompt_version: string;
            /** Provider */
            provider: string;
            /** Rule Version */
            rule_version: string;
            /** Status */
            status: string;
            /** Subject Id */
            subject_id: string | null;
            /** Summary */
            summary: string;
            /** Topic */
            topic: string | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * AnswerCheck
         * @enum {string}
         */
        AnswerCheck: "pending" | "checked";
        /** AttachmentData */
        AttachmentData: {
            /** Byte Size */
            byte_size: number | null;
            /** Created At */
            created_at: string;
            /** Detected Mime */
            detected_mime: string | null;
            /** Expires At */
            expires_at: string;
            /** Failure Code */
            failure_code: string | null;
            /** Id */
            id: string;
            /** Original Name */
            original_name: string;
            /** Page Count */
            page_count: number | null;
            /** Sha256 */
            sha256: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "pending_upload" | "uploaded" | "validating" | "ready" | "rejected" | "expired";
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** AttachmentJobData */
        AttachmentJobData: {
            /** Attachment Id */
            attachment_id: string;
            /** Attempt Count */
            attempt_count: number;
            /** Error Code */
            error_code: string | null;
            /** Id */
            id: string;
            /** Input Version */
            input_version: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "validate" | "preview";
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed";
        };
        /** AttachmentLinkData */
        AttachmentLinkData: {
            /** Attachment Id */
            attachment_id: string;
            /** Byte Size */
            byte_size: number;
            /** Detected Mime */
            detected_mime: string;
            /** Link Id */
            link_id: string;
            /** Original Name */
            original_name: string;
            /** Page End */
            page_end: number | null;
            /** Page Start */
            page_start: number | null;
            /**
             * Role
             * @enum {string}
             */
            role: "question" | "attempt" | "answer" | "source";
            /**
             * Status
             * @constant
             */
            status: "ready";
        };
        /**
         * AttachmentRole
         * @enum {string}
         */
        AttachmentRole: "question" | "attempt" | "answer" | "source";
        /** AuthData */
        AuthData: {
            /** Csrf Token */
            csrf_token: string;
            user: components["schemas"]["UserData"];
        };
        /** CancelAdvisorInput */
        CancelAdvisorInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** CancelDeletionInput */
        CancelDeletionInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** ChapterData */
        ChapterData: {
            /** Archived */
            archived: boolean;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Order Index */
            order_index: number;
            /** Subject Id */
            subject_id: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** ChapterPageData */
        ChapterPageData: {
            /** Items */
            items: components["schemas"]["ChapterData"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CitedText */
        CitedText: {
            /** Source Refs */
            source_refs: string[];
            /** Text */
            text: string;
        };
        /** ComparisonData */
        ComparisonData: {
            /** Archived */
            archived: boolean;
            /** Assumptions */
            assumptions: string | null;
            /** Boundary */
            boundary: string | null;
            /** Conclusion */
            conclusion: string | null;
            /** Conditions */
            conditions: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Diagram */
            diagram: string | null;
            /** Entry Point */
            entry_point: string | null;
            /** Formulas */
            formulas: string | null;
            /** Id */
            id: string;
            /** Known Values */
            known_values: string | null;
            /** Left Attempt Id */
            left_attempt_id: string | null;
            /** Left Problem Id */
            left_problem_id: string;
            /** Right Attempt Id */
            right_attempt_id: string | null;
            /** Right Problem Id */
            right_problem_id: string;
            /** Source Changed */
            source_changed: boolean;
            /** Source Versions */
            source_versions: {
                [key: string]: number;
            };
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** ComparisonPageData */
        ComparisonPageData: {
            /** Items */
            items: components["schemas"]["ComparisonData"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CompleteInput */
        CompleteInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /**
         * CorrectTimeSegmentInput
         * @description Corrections may only shorten a span or exclude it, never extend it.
         */
        CorrectTimeSegmentInput: {
            /** Correction Note */
            correction_note?: string | null;
            /** Ended At */
            ended_at?: string | null;
            /** Exclude */
            exclude?: boolean | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** CreateAdvisorInput */
        CreateAdvisorInput: {
            /** Knowledge Point Id */
            knowledge_point_id?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Subject Id */
            subject_id?: string | null;
            /** Topic */
            topic?: string | null;
        };
        /** CreateAttempt */
        CreateAttempt: {
            answer_check: components["schemas"]["AnswerCheck"];
            /** Attempt Text */
            attempt_text?: string | null;
            /** Error Categories */
            error_categories?: components["schemas"]["ErrorCategory"][];
            independence: components["schemas"]["Independence"];
            /** Occurred At */
            occurred_at?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Other Error Note */
            other_error_note?: string | null;
            /**
             * Problem Id
             * Format: uuid
             */
            problem_id: string;
            result?: components["schemas"]["Result"] | null;
            /**
             * Session Id
             * Format: uuid
             */
            session_id: string;
            /** Stuck Note */
            stuck_note?: string | null;
        };
        /** CreateChapterInput */
        CreateChapterInput: {
            /** Name */
            name: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /**
             * Order Index
             * @default 0
             */
            order_index: number;
            /**
             * Subject Id
             * Format: uuid
             */
            subject_id: string;
        };
        /** CreateComparisonInput */
        CreateComparisonInput: {
            /** Assumptions */
            assumptions?: string | null;
            /** Boundary */
            boundary?: string | null;
            /** Conclusion */
            conclusion?: string | null;
            /** Conditions */
            conditions?: string | null;
            /** Diagram */
            diagram?: string | null;
            /** Entry Point */
            entry_point?: string | null;
            /** Formulas */
            formulas?: string | null;
            /** Known Values */
            known_values?: string | null;
            /** Left Attempt Id */
            left_attempt_id?: string | null;
            /**
             * Left Problem Id
             * Format: uuid
             */
            left_problem_id: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Right Attempt Id */
            right_attempt_id?: string | null;
            /**
             * Right Problem Id
             * Format: uuid
             */
            right_problem_id: string;
        };
        /** CreateDeletionInput */
        CreateDeletionInput: {
            /** Confirmation */
            confirmation: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** CreatedMasteryAssessmentData */
        CreatedMasteryAssessmentData: {
            assessment: components["schemas"]["MasteryAssessmentData"];
            /** Knowledge Point Version */
            knowledge_point_version: number;
        };
        /** CreateExportInput */
        CreateExportInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** CreateKnowledgePointInput */
        CreateKnowledgePointInput: {
            /**
             * Chapter Id
             * Format: uuid
             */
            chapter_id: string;
            /** Name */
            name: string;
            /** Notes */
            notes?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** CreateMasteryAssessment */
        CreateMasteryAssessment: {
            /** Evidence Attempt Ids */
            evidence_attempt_ids?: string[];
            /**
             * Knowledge Point Id
             * Format: uuid
             */
            knowledge_point_id: string;
            level: components["schemas"]["MasteryLevel"];
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Reason */
            reason?: string | null;
            /** Variant Note */
            variant_note?: string | null;
        };
        /** CreateProblem */
        CreateProblem: {
            /** Attachment Links */
            attachment_links?: components["schemas"]["ProblemAttachmentInput"][];
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Source Note */
            source_note?: string | null;
            /** Statement */
            statement?: string | null;
            /** Subject Id */
            subject_id?: string | null;
            /** Title */
            title?: string | null;
        };
        /** CreateReflection */
        CreateReflection: {
            /** Missing Parts */
            missing_parts?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Recalled Text */
            recalled_text?: string | null;
            /** Reference Checked */
            reference_checked?: boolean | null;
            /** Resume Note */
            resume_note?: string | null;
            /**
             * Session Id
             * Format: uuid
             */
            session_id: string;
            /** Stuck Note */
            stuck_note?: string | null;
            /** Summary */
            summary?: string | null;
        };
        /** CreateSessionInput */
        CreateSessionInput: {
            /** Goal */
            goal?: string | null;
            /**
             * Kind
             * @default free
             * @enum {string}
             */
            kind: "problem" | "recall" | "reading" | "free";
            /** Knowledge Point Id */
            knowledge_point_id?: string | null;
            /** Method Id */
            method_id?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Previous Session Id */
            previous_session_id?: string | null;
            /** Resume Note */
            resume_note?: string | null;
            /** Subject Id */
            subject_id?: string | null;
            /**
             * Timing Enabled
             * @default false
             */
            timing_enabled: boolean;
        };
        /** CreateStuckPointInput */
        CreateStuckPointInput: {
            /** Attempt Id */
            attempt_id?: string | null;
            /** Knowledge Point Id */
            knowledge_point_id?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /**
             * Session Id
             * Format: uuid
             */
            session_id: string;
            /** Text */
            text: string;
        };
        /** DailyQuoteData */
        DailyQuoteData: {
            /** Day Timezone */
            day_timezone: string;
            /** Local Date */
            local_date: string;
            preference?: components["schemas"]["QuotePreferenceData"] | null;
            quote: components["schemas"]["QuoteData"] | null;
            /** Reason */
            reason?: string | null;
        };
        /** DaySummaryData */
        DaySummaryData: {
            /** Changes */
            changes: components["schemas"]["SummaryTextItem"][];
            /** Checked Count */
            checked_count: number;
            /**
             * Date
             * Format: date
             */
            date: string;
            /** Effective Record Count */
            effective_record_count: number;
            /** Error Categories */
            error_categories: components["schemas"]["ErrorCategoryData"][];
            /** Independent Correct Count */
            independent_correct_count: number;
            /** Learned */
            learned: components["schemas"]["SummaryTextItem"][];
            /** Pending Count */
            pending_count: number;
            /** Review Candidates */
            review_candidates: components["schemas"]["SummaryTextItem"][];
            /** Rule Version */
            rule_version: string;
            /** Session Count */
            session_count: number;
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
            /** Source Revision */
            source_revision: string;
            /** Stuck Points */
            stuck_points: components["schemas"]["SummaryTextItem"][];
            /** Timezone */
            timezone: string;
        };
        /** EndSessionInput */
        EndSessionInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** Envelope[AccountDeletionData] */
        Envelope_AccountDeletionData_: {
            data: components["schemas"]["AccountDeletionData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AccountExportData] */
        Envelope_AccountExportData_: {
            data: components["schemas"]["AccountExportData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AccountExportPageData] */
        Envelope_AccountExportPageData_: {
            data: components["schemas"]["AccountExportPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AccountStatusData] */
        Envelope_AccountStatusData_: {
            data: components["schemas"]["AccountStatusData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AdvisorPageData] */
        Envelope_AdvisorPageData_: {
            data: components["schemas"]["AdvisorPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AdvisorRunData] */
        Envelope_AdvisorRunData_: {
            data: components["schemas"]["AdvisorRunData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AttachmentData] */
        Envelope_AttachmentData_: {
            data: components["schemas"]["AttachmentData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AttachmentJobData] */
        Envelope_AttachmentJobData_: {
            data: components["schemas"]["AttachmentJobData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[AuthData] */
        Envelope_AuthData_: {
            data: components["schemas"]["AuthData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ChapterData] */
        Envelope_ChapterData_: {
            data: components["schemas"]["ChapterData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ChapterPageData] */
        Envelope_ChapterPageData_: {
            data: components["schemas"]["ChapterPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ComparisonData] */
        Envelope_ComparisonData_: {
            data: components["schemas"]["ComparisonData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ComparisonPageData] */
        Envelope_ComparisonPageData_: {
            data: components["schemas"]["ComparisonPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[CreatedMasteryAssessmentData] */
        Envelope_CreatedMasteryAssessmentData_: {
            data: components["schemas"]["CreatedMasteryAssessmentData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[DaySummaryData] */
        Envelope_DaySummaryData_: {
            data: components["schemas"]["DaySummaryData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ExportDownloadData] */
        Envelope_ExportDownloadData_: {
            data: components["schemas"]["ExportDownloadData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[HealthData] */
        Envelope_HealthData_: {
            data: components["schemas"]["HealthData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[HomeData] */
        Envelope_HomeData_: {
            data: components["schemas"]["HomeData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[KnowledgePointData] */
        Envelope_KnowledgePointData_: {
            data: components["schemas"]["KnowledgePointData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[KnowledgePointEvidenceData] */
        Envelope_KnowledgePointEvidenceData_: {
            data: components["schemas"]["KnowledgePointEvidenceData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[KnowledgePointPageData] */
        Envelope_KnowledgePointPageData_: {
            data: components["schemas"]["KnowledgePointPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[LearningMethodData] */
        Envelope_LearningMethodData_: {
            data: components["schemas"]["LearningMethodData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[LearningMethodsData] */
        Envelope_LearningMethodsData_: {
            data: components["schemas"]["LearningMethodsData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[LearningSituationData] */
        Envelope_LearningSituationData_: {
            data: components["schemas"]["LearningSituationData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[LearningSituationsData] */
        Envelope_LearningSituationsData_: {
            data: components["schemas"]["LearningSituationsData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemAttachmentLinksData] */
        Envelope_ProblemAttachmentLinksData_: {
            data: components["schemas"]["ProblemAttachmentLinksData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemAttachmentLinkWriteData] */
        Envelope_ProblemAttachmentLinkWriteData_: {
            data: components["schemas"]["ProblemAttachmentLinkWriteData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemAttachmentUnlinkData] */
        Envelope_ProblemAttachmentUnlinkData_: {
            data: components["schemas"]["ProblemAttachmentUnlinkData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemAttemptData] */
        Envelope_ProblemAttemptData_: {
            data: components["schemas"]["ProblemAttemptData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemData] */
        Envelope_ProblemData_: {
            data: components["schemas"]["ProblemData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemKnowledgeLinksData] */
        Envelope_ProblemKnowledgeLinksData_: {
            data: components["schemas"]["ProblemKnowledgeLinksData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProblemPageData] */
        Envelope_ProblemPageData_: {
            data: components["schemas"]["ProblemPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ProductMeta] */
        Envelope_ProductMeta_: {
            data: components["schemas"]["ProductMeta"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[QuoteFavoritesData] */
        Envelope_QuoteFavoritesData_: {
            data: components["schemas"]["QuoteFavoritesData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[QuotePreferenceResultData] */
        Envelope_QuotePreferenceResultData_: {
            data: components["schemas"]["QuotePreferenceResultData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[QuoteTodayData] */
        Envelope_QuoteTodayData_: {
            data: components["schemas"]["QuoteTodayData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[RecordsPageData] */
        Envelope_RecordsPageData_: {
            data: components["schemas"]["RecordsPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[ReflectionData] */
        Envelope_ReflectionData_: {
            data: components["schemas"]["ReflectionData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SessionData] */
        Envelope_SessionData_: {
            data: components["schemas"]["SessionData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SessionHistoryData] */
        Envelope_SessionHistoryData_: {
            data: components["schemas"]["SessionHistoryData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[StuckPointData] */
        Envelope_StuckPointData_: {
            data: components["schemas"]["StuckPointData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[StuckPointPageData] */
        Envelope_StuckPointPageData_: {
            data: components["schemas"]["StuckPointPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SubjectsData] */
        Envelope_SubjectsData_: {
            data: components["schemas"]["SubjectsData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SubjectSpaceData] */
        Envelope_SubjectSpaceData_: {
            data: components["schemas"]["SubjectSpaceData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SuggestionData] */
        Envelope_SuggestionData_: {
            data: components["schemas"]["SuggestionData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[SuggestionPageData] */
        Envelope_SuggestionPageData_: {
            data: components["schemas"]["SuggestionPageData"];
            meta: components["schemas"]["Meta"];
        };
        /** Envelope[Union[SessionData, NoneType]] */
        Envelope_Union_SessionData__NoneType__: {
            data: components["schemas"]["SessionData"] | null;
            meta: components["schemas"]["Meta"];
        };
        /**
         * ErrorCategory
         * @enum {string}
         */
        ErrorCategory: "concept" | "modeling" | "condition" | "formula" | "derivation" | "calculation" | "sign" | "unit" | "reading" | "other";
        /** ErrorCategoryData */
        ErrorCategoryData: {
            /** Category */
            category: string;
            /** Count */
            count: number;
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
        };
        /** ErrorCategoryEvidence */
        ErrorCategoryEvidence: {
            /** Attempt Count */
            attempt_count: number;
            category: components["schemas"]["ErrorCategory"];
            /** Source Refs */
            source_refs: components["schemas"]["EvidenceSourceRef"][];
        };
        /** ErrorData */
        ErrorData: {
            /** Code */
            code: string;
            /** Current */
            current?: {
                [key: string]: unknown;
            } | null;
            /** Current Version */
            current_version?: number | null;
            /** Message */
            message: string;
            /** Request Id */
            request_id: string;
        };
        /** ErrorEnvelope */
        ErrorEnvelope: {
            error: components["schemas"]["ErrorData"];
        };
        /** EvidenceCounts */
        EvidenceCounts: {
            /** Attempt Count */
            attempt_count: number;
            /** Checked Correct Count */
            checked_correct_count: number;
            /** Checked Correct Rate */
            checked_correct_rate: number | null;
            /** Checked Count */
            checked_count: number;
            /** Independent Correct Count */
            independent_correct_count: number;
            /** Pending Count */
            pending_count: number;
        };
        /** EvidenceEligibilityData */
        EvidenceEligibilityData: {
            /** Eligible */
            eligible: boolean;
            /** Reason */
            reason: string;
        };
        /** EvidenceRef */
        EvidenceRef: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** Label */
            label: string | null;
            /** Version */
            version: number;
        };
        /** EvidenceSourceRef */
        EvidenceSourceRef: {
            /** Attempt Id */
            attempt_id: string;
            /** Attempt Version */
            attempt_version: number;
            /** Problem Id */
            problem_id: string;
            /** Problem Version */
            problem_version: number;
        };
        /** ExportDownloadData */
        ExportDownloadData: {
            /** Byte Size */
            byte_size: number;
            /** Document */
            document: {
                [key: string]: unknown;
            };
            /** Expires At */
            expires_at: string | null;
            /** Id */
            id: string;
            /** Sha256 */
            sha256: string | null;
        };
        /** HealthData */
        HealthData: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** HomeChangesData */
        HomeChangesData: {
            /** Effective Learning Days */
            effective_learning_days: number;
            /**
             * From Date
             * Format: date
             */
            from_date: string;
            /** Items */
            items: components["schemas"]["SummaryTextItem"][];
            /** Rule Version */
            rule_version: string;
            /** Source Revision */
            source_revision: string;
            /**
             * To Date
             * Format: date
             */
            to_date: string;
        };
        /** HomeContinueData */
        HomeContinueData: {
            current: components["schemas"]["SessionData"] | null;
            last: components["schemas"]["RecordData"] | null;
        };
        /** HomeData */
        HomeData: {
            /**
             * Date
             * Format: date
             */
            date: string;
            /** Rule Version */
            rule_version: string;
            sections: components["schemas"]["HomeSections"];
            /** Timezone */
            timezone: string;
        };
        /** HomeMethodsData */
        HomeMethodsData: {
            /** Items */
            items: components["schemas"]["HomeMethodSummary"][];
        };
        /** HomeMethodSummary */
        HomeMethodSummary: {
            /** Content Version */
            content_version: number;
            /** Id */
            id: string;
            /** Summary */
            summary: string;
            /** Title */
            title: string;
        };
        /** HomeReviewData */
        HomeReviewData: {
            /** Has More */
            has_more: boolean;
            /** Items */
            items: components["schemas"]["SuggestionData"][];
        };
        /** HomeSection[HomeChangesData] */
        HomeSection_HomeChangesData_: {
            data?: components["schemas"]["HomeChangesData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[HomeContinueData] */
        HomeSection_HomeContinueData_: {
            data?: components["schemas"]["HomeContinueData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[HomeMethodsData] */
        HomeSection_HomeMethodsData_: {
            data?: components["schemas"]["HomeMethodsData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[HomeReviewData] */
        HomeSection_HomeReviewData_: {
            data?: components["schemas"]["HomeReviewData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[HomeSuggestionsData] */
        HomeSection_HomeSuggestionsData_: {
            data?: components["schemas"]["HomeSuggestionsData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[QuoteTodayData] */
        HomeSection_QuoteTodayData_: {
            data?: components["schemas"]["QuoteTodayData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSection[SubjectsData] */
        HomeSection_SubjectsData_: {
            data?: components["schemas"]["SubjectsData"] | null;
            error?: components["schemas"]["HomeSectionError"] | null;
            /** Source Revision */
            source_revision?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "empty" | "unavailable";
        };
        /** HomeSectionError */
        HomeSectionError: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** HomeSections */
        HomeSections: {
            changes?: components["schemas"]["HomeSection_HomeChangesData_"] | null;
            continue_learning?: components["schemas"]["HomeSection_HomeContinueData_"] | null;
            methods?: components["schemas"]["HomeSection_HomeMethodsData_"] | null;
            quote?: components["schemas"]["HomeSection_QuoteTodayData_"] | null;
            review?: components["schemas"]["HomeSection_HomeReviewData_"] | null;
            subjects?: components["schemas"]["HomeSection_SubjectsData_"] | null;
            suggestions?: components["schemas"]["HomeSection_HomeSuggestionsData_"] | null;
        };
        /** HomeSuggestionsData */
        HomeSuggestionsData: {
            /** Has More */
            has_more: boolean;
            /** Items */
            items: components["schemas"]["SuggestionData"][];
        };
        /**
         * Independence
         * @enum {string}
         */
        Independence: "independent" | "hinted" | "after_answer" | "unable";
        /** KnowledgePointData */
        KnowledgePointData: {
            /** Archived */
            archived: boolean;
            /** Chapter Id */
            chapter_id: string;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Notes */
            notes: string | null;
            /** Subject Id */
            subject_id: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** KnowledgePointEvidenceData */
        KnowledgePointEvidenceData: {
            /** Assessments */
            assessments: components["schemas"]["MasteryAssessmentData"][];
            counts: components["schemas"]["EvidenceCounts"];
            /** Error Categories */
            error_categories: components["schemas"]["ErrorCategoryEvidence"][];
            /** Knowledge Point Id */
            knowledge_point_id: string;
            /** Knowledge Point Version */
            knowledge_point_version: number;
            recent_checked_streak: components["schemas"]["RecentCheckedStreak"];
            /** Rule Version */
            rule_version: string;
            /** Source Refs */
            source_refs: components["schemas"]["EvidenceSourceRef"][];
            /** Source Revision */
            source_revision: string;
        };
        /** KnowledgePointPageData */
        KnowledgePointPageData: {
            /** Items */
            items: components["schemas"]["KnowledgePointData"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** LearningMethodData */
        LearningMethodData: {
            /** Content Version */
            content_version: number;
            /** Id */
            id: string;
            /** Pitfalls */
            pitfalls: string[];
            /** Problem */
            problem: string;
            /** Situations */
            situations: string[];
            /** Steps */
            steps: string[];
            /** Summary */
            summary: string;
            /** Title */
            title: string;
        };
        /** LearningMethodsData */
        LearningMethodsData: {
            /** Items */
            items: components["schemas"]["LearningMethodData"][];
        };
        /** LearningSituationData */
        LearningSituationData: {
            /** Allow Free Learning */
            allow_free_learning: boolean;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Method Ids */
            method_ids: string[];
            /** Reason */
            reason: string;
        };
        /** LearningSituationsData */
        LearningSituationsData: {
            /** Items */
            items: components["schemas"]["LearningSituationData"][];
        };
        /** LinkProblemAttachment */
        LinkProblemAttachment: {
            /**
             * Attachment Id
             * Format: uuid
             */
            attachment_id: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Page End */
            page_end?: number | null;
            /** Page Start */
            page_start?: number | null;
            role: components["schemas"]["AttachmentRole"];
        };
        /** LoginInput */
        LoginInput: {
            /** Password */
            password: string;
            /** Username */
            username: string;
        };
        /** MasteryAssessmentData */
        MasteryAssessmentData: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Evidence Message */
            evidence_message: string;
            /**
             * Evidence Status
             * @enum {string}
             */
            evidence_status: "unsupported" | "current" | "stale";
            /** Id */
            id: string;
            /** Knowledge Point Version */
            knowledge_point_version: number;
            level: components["schemas"]["MasteryLevel"];
            /** Reason */
            reason: string | null;
            /** Source Refs */
            source_refs: components["schemas"]["EvidenceSourceRef"][];
            /** Variant Note */
            variant_note: string | null;
            /** Version */
            version: number;
        };
        /**
         * MasteryLevel
         * @enum {string}
         */
        MasteryLevel: "unfamiliar" | "encountered" | "typical" | "independent" | "variant_stable";
        /** Meta */
        Meta: {
            /** Request Id */
            request_id: string;
        };
        /** PatchChapterInput */
        PatchChapterInput: {
            /** Archived */
            archived?: boolean | null;
            /** Name */
            name?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Order Index */
            order_index?: number | null;
        };
        /** PatchComparisonInput */
        PatchComparisonInput: {
            /** Archived */
            archived?: boolean | null;
            /** Assumptions */
            assumptions?: string | null;
            /** Boundary */
            boundary?: string | null;
            /** Conclusion */
            conclusion?: string | null;
            /** Conditions */
            conditions?: string | null;
            /** Diagram */
            diagram?: string | null;
            /** Entry Point */
            entry_point?: string | null;
            /** Formulas */
            formulas?: string | null;
            /** Known Values */
            known_values?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** PatchKnowledgePointInput */
        PatchKnowledgePointInput: {
            /** Archived */
            archived?: boolean | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** PatchStuckPointInput */
        PatchStuckPointInput: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Resolution Note */
            resolution_note?: string | null;
            /** Status */
            status?: ("open" | "resolved") | null;
            /** Text */
            text?: string | null;
        };
        /** PreviewJobInput */
        PreviewJobInput: {
            /**
             * Kind
             * @default preview
             */
            kind: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Page */
            page: number;
        };
        /** ProblemAttachmentInput */
        ProblemAttachmentInput: {
            /**
             * Attachment Id
             * Format: uuid
             */
            attachment_id: string;
            /** Page End */
            page_end?: number | null;
            /** Page Start */
            page_start?: number | null;
            role: components["schemas"]["AttachmentRole"];
        };
        /** ProblemAttachmentLinksData */
        ProblemAttachmentLinksData: {
            /** Items */
            items: components["schemas"]["AttachmentLinkData"][];
            /** Problem Version */
            problem_version: number;
        };
        /** ProblemAttachmentLinkWriteData */
        ProblemAttachmentLinkWriteData: {
            link: components["schemas"]["AttachmentLinkData"];
            /** Problem Version */
            problem_version: number;
        };
        /** ProblemAttachmentUnlinkData */
        ProblemAttachmentUnlinkData: {
            /** Problem Version */
            problem_version: number;
        };
        /** ProblemAttemptData */
        ProblemAttemptData: {
            /**
             * Answer Check
             * @enum {string}
             */
            answer_check: "pending" | "checked";
            /** Attempt Text */
            attempt_text: string | null;
            /** Created At */
            created_at: string;
            /** Error Categories */
            error_categories: ("concept" | "modeling" | "condition" | "formula" | "derivation" | "calculation" | "sign" | "unit" | "reading" | "other")[];
            evidence_eligibility: components["schemas"]["EvidenceEligibilityData"];
            /** Id */
            id: string;
            /**
             * Independence
             * @enum {string}
             */
            independence: "independent" | "hinted" | "after_answer" | "unable";
            /** Occurred At */
            occurred_at: string;
            /** Other Error Note */
            other_error_note?: string | null;
            /** Problem Id */
            problem_id: string;
            /** Result */
            result: ("correct" | "partial" | "incorrect") | null;
            /** Session Id */
            session_id: string;
            /** Stuck Note */
            stuck_note: string | null;
            /** Updated At */
            updated_at: string;
            /** Verified At */
            verified_at: string | null;
            /** Version */
            version: number;
        };
        /** ProblemData */
        ProblemData: {
            /** Archived */
            archived: boolean;
            /** Attachment Links */
            attachment_links?: components["schemas"]["AttachmentLinkData"][];
            /** Attempts */
            attempts?: components["schemas"]["ProblemAttemptData"][];
            /** Correct Answer */
            correct_answer: string | null;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Is Representative */
            is_representative: boolean;
            /** Knowledge Point Ids */
            knowledge_point_ids?: string[];
            /** Source Note */
            source_note: string | null;
            /** Statement */
            statement: string | null;
            /** Subject Id */
            subject_id: string | null;
            /** Title */
            title: string | null;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** ProblemKnowledgeLinksData */
        ProblemKnowledgeLinksData: {
            /** Knowledge Point Ids */
            knowledge_point_ids: string[];
            problem: components["schemas"]["ProblemData"];
        };
        /** ProblemKnowledgeLinksInput */
        ProblemKnowledgeLinksInput: {
            /** Knowledge Point Ids */
            knowledge_point_ids: string[];
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** ProblemPageData */
        ProblemPageData: {
            /** Items */
            items: components["schemas"]["ProblemData"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ProblemPatchInput */
        ProblemPatchInput: {
            /** Archived */
            archived?: boolean | null;
            /** Correct Answer */
            correct_answer?: string | null;
            /** Is Representative */
            is_representative?: boolean | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Source Note */
            source_note?: string | null;
            /** Statement */
            statement?: string | null;
            /** Title */
            title?: string | null;
        };
        /** ProductMeta */
        ProductMeta: {
            /**
             * Agent Mode
             * @default mock
             * @constant
             */
            agent_mode: "mock";
            /** Environment */
            environment: string;
            /**
             * Name
             * @default Hermes
             * @constant
             */
            name: "Hermes";
            /**
             * Version
             * @default 0.1.0
             * @constant
             */
            version: "0.1.0";
        };
        /** PurgeDeletionInput */
        PurgeDeletionInput: {
            /** Confirmation */
            confirmation: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** QuoteData */
        QuoteData: {
            /** Author */
            author?: string | null;
            /** Id */
            id: string;
            /** Text */
            text: string;
        };
        /** QuoteFavoritesData */
        QuoteFavoritesData: {
            /** Disliked */
            disliked: components["schemas"]["QuotePreferenceData"][];
            /** Items */
            items: components["schemas"]["QuotePreferenceData"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** QuotePreferenceData */
        QuotePreferenceData: {
            /** Disliked */
            disliked: boolean;
            /** Favorited */
            favorited: boolean;
            /** Quote Id */
            quote_id: string;
            /** Text */
            text: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** QuotePreferenceInput */
        QuotePreferenceInput: {
            /** Disliked */
            disliked: boolean;
            /** Favorited */
            favorited: boolean;
        };
        /** QuotePreferenceResultData */
        QuotePreferenceResultData: {
            daily_quote?: components["schemas"]["DailyQuoteData"] | null;
            preference: components["schemas"]["QuotePreferenceData"];
        };
        /** QuoteTodayData */
        QuoteTodayData: {
            daily_quote: components["schemas"]["DailyQuoteData"];
        };
        /** RecentCheckedStreak */
        RecentCheckedStreak: {
            /** Count */
            count: number;
            /** Label */
            label: string;
            /** Pending Count */
            pending_count: number;
            /** Source Refs */
            source_refs: components["schemas"]["EvidenceSourceRef"][];
        };
        /** RecordData */
        RecordData: {
            /** Attempt Count */
            attempt_count: number;
            /** Checked Count */
            checked_count: number;
            /** Day Timezone */
            day_timezone: string;
            /** Effective */
            effective: boolean;
            /** Ended At */
            ended_at: string | null;
            /** Goal */
            goal: string | null;
            /** Id */
            id: string;
            /** Independent Correct Count */
            independent_correct_count: number;
            /**
             * Learning Date
             * Format: date
             */
            learning_date: string;
            /** Missing Parts */
            missing_parts: string | null;
            /** Pending Count */
            pending_count: number;
            /** Recalled Text */
            recalled_text: string | null;
            /** Resume Note */
            resume_note: string | null;
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "paused" | "ended" | "cancelled";
            /** Stuck Note */
            stuck_note: string | null;
            /** Subject Id */
            subject_id: string | null;
            /** Subject Name */
            subject_name?: string | null;
            /** Summary */
            summary: string | null;
            /** Version */
            version: number;
        };
        /** RecordsPageData */
        RecordsPageData: {
            /**
             * From Date
             * Format: date
             */
            from_date: string;
            /** Items */
            items: components["schemas"]["RecordData"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Rule Version */
            rule_version: string;
            /** Source Revision */
            source_revision: string;
            /** Timezone */
            timezone: string;
            /**
             * To Date
             * Format: date
             */
            to_date: string;
            totals: components["schemas"]["RecordsTotals"];
        };
        /** RecordsTotals */
        RecordsTotals: {
            /** Checked Count */
            checked_count: number;
            /** Effective Record Count */
            effective_record_count: number;
            /** Independent Correct Count */
            independent_correct_count: number;
            /** Pending Count */
            pending_count: number;
            /** Session Count */
            session_count: number;
        };
        /** ReflectionData */
        ReflectionData: {
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Missing Parts */
            missing_parts: string | null;
            /** Recalled Text */
            recalled_text: string | null;
            /** Reference Checked */
            reference_checked: boolean | null;
            /** Resume Note */
            resume_note: string | null;
            /** Session Id */
            session_id: string;
            /** Stuck Note */
            stuck_note: string | null;
            /** Summary */
            summary: string | null;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /**
         * Result
         * @enum {string}
         */
        Result: "correct" | "partial" | "incorrect";
        /** SessionData */
        SessionData: {
            /** Day Timezone */
            day_timezone: string;
            /** Effective Duration Seconds */
            effective_duration_seconds: number;
            /** Ended At */
            ended_at: string | null;
            /** Goal */
            goal: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @default free
             * @enum {string}
             */
            kind: "problem" | "recall" | "reading" | "free";
            /** Knowledge Point Id */
            knowledge_point_id?: string | null;
            /** Learning Date */
            learning_date: string;
            /** Method Id */
            method_id: string | null;
            /** Previous Session Id */
            previous_session_id?: string | null;
            /** Resume Note */
            resume_note?: string | null;
            /** Started At */
            started_at: string;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "paused" | "ended" | "cancelled";
            /** Subject Id */
            subject_id: string | null;
            /** Time Segments */
            time_segments: components["schemas"]["SessionTimeSegmentData"][];
            /** Timing Enabled */
            timing_enabled: boolean;
            /**
             * Timing Review Required
             * @default false
             */
            timing_review_required: boolean;
            /** Version */
            version: number;
        };
        /** SessionHistoryData */
        SessionHistoryData: {
            /** Items */
            items: components["schemas"]["SessionData"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** SessionTimeSegmentData */
        SessionTimeSegmentData: {
            /** Anomalies */
            anomalies?: string[];
            /** Correction Note */
            correction_note?: string | null;
            /** Duration Seconds */
            duration_seconds: number;
            /** Ended At */
            ended_at: string | null;
            /**
             * Excluded
             * @default false
             */
            excluded: boolean;
            /** Excluded At */
            excluded_at?: string | null;
            /** Id */
            id: string;
            /** Original Ended At */
            original_ended_at?: string | null;
            /**
             * Review Required
             * @default false
             */
            review_required: boolean;
            /** Started At */
            started_at: string;
        };
        /** SourceRef */
        SourceRef: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "session" | "reflection" | "attempt" | "problem" | "knowledge_point";
            /** Label */
            label: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Problem Id */
            problem_id?: string | null;
            /** Session Id */
            session_id?: string | null;
            /** Version */
            version: number;
        };
        /** StuckPointData */
        StuckPointData: {
            /** Attempt Id */
            attempt_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Id */
            id: string;
            /** Knowledge Point Id */
            knowledge_point_id: string | null;
            /** Resolution Note */
            resolution_note: string | null;
            /** Resolved At */
            resolved_at: string | null;
            /** Session Id */
            session_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "resolved";
            /** Text */
            text: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** StuckPointPageData */
        StuckPointPageData: {
            /** Items */
            items: components["schemas"]["StuckPointData"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** SubjectData */
        SubjectData: {
            /** Group Label */
            group_label?: string | null;
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** SubjectsData */
        SubjectsData: {
            /** Items */
            items: components["schemas"]["SubjectData"][];
        };
        /** SubjectSpaceData */
        SubjectSpaceData: {
            /** Chapters */
            chapters: components["schemas"]["ChapterData"][];
            /** Chapters Next Cursor */
            chapters_next_cursor?: string | null;
            /** Recent Problems */
            recent_problems: components["schemas"]["ProblemData"][];
            /** Recent Sessions */
            recent_sessions: components["schemas"]["SessionData"][];
            subject: components["schemas"]["SubjectData"];
        };
        /** SuggestionActionInput */
        SuggestionActionInput: {
            /**
             * Action
             * @enum {string}
             */
            action: "accept" | "snooze" | "dismiss";
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Snoozed Until */
            snoozed_until?: string | null;
        };
        /** SuggestionData */
        SuggestionData: {
            /** Expires At */
            expires_at?: string | null;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "continue" | "unverified" | "review" | "repeated_error";
            /** Knowledge Point Id */
            knowledge_point_id?: string | null;
            /** Problem Id */
            problem_id?: string | null;
            /** Reason */
            reason: string;
            /** Rule Version */
            rule_version: string;
            /** Snoozed Until */
            snoozed_until?: string | null;
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
            /** Source Revision */
            source_revision: string;
            /**
             * Status
             * @enum {string}
             */
            status: "available" | "accepted" | "snoozed" | "dismissed" | "stale";
            /** Subject Id */
            subject_id?: string | null;
            /** Version */
            version: number;
        };
        /** SuggestionPageData */
        SuggestionPageData: {
            /** Items */
            items: components["schemas"]["SuggestionData"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Rule Version */
            rule_version: string;
        };
        /** SummaryTextItem */
        SummaryTextItem: {
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
            /** Text */
            text: string;
        };
        /** UnlinkProblemAttachment */
        UnlinkProblemAttachment: {
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
        };
        /** UpdateAttempt */
        UpdateAttempt: {
            answer_check?: components["schemas"]["AnswerCheck"] | null;
            /** Attempt Text */
            attempt_text?: string | null;
            /** Error Categories */
            error_categories?: components["schemas"]["ErrorCategory"][] | null;
            independence?: components["schemas"]["Independence"] | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Other Error Note */
            other_error_note?: string | null;
            result?: components["schemas"]["Result"] | null;
            /** Stuck Note */
            stuck_note?: string | null;
        };
        /** UpdateReflection */
        UpdateReflection: {
            /** Missing Parts */
            missing_parts?: string | null;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Recalled Text */
            recalled_text?: string | null;
            /** Reference Checked */
            reference_checked?: boolean | null;
            /** Resume Note */
            resume_note?: string | null;
            /** Stuck Note */
            stuck_note?: string | null;
            /** Summary */
            summary?: string | null;
        };
        /** UploadInit */
        UploadInit: {
            /** Byte Size */
            byte_size: number;
            /** Declared Mime */
            declared_mime: string;
            /** Filename */
            filename: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /** Sha256 */
            sha256?: string | null;
        };
        /** UserData */
        UserData: {
            /** Id */
            id: string;
            /** Timezone */
            timezone: string;
            /** Username */
            username: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    status_api_v1_account_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountStatusData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    request_deletion_api_v1_account_deletion_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateDeletionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountDeletionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    cancel_deletion_api_v1_account_deletion_cancel_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CancelDeletionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountDeletionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    purge_deletion_api_v1_account_deletion_purge_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PurgeDeletionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountDeletionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    list_exports_api_v1_account_exports_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountExportPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_export_api_v1_account_exports_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateExportInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AccountExportData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    download_export_api_v1_account_exports__export_id__download_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ExportDownloadData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    list_items_api_v1_advisor_analyses_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AdvisorPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_api_v1_advisor_analyses_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateAdvisorInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AdvisorRunData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_api_v1_advisor_analyses__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AdvisorRunData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    cancel_api_v1_advisor_analyses__run_id__cancel_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CancelAdvisorInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AdvisorRunData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_attachment_api_v1_attachments__attachment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    complete_api_v1_attachments__attachment_id__complete_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompleteInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentJobData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    content_api_v1_attachments__attachment_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                    "application/octet-stream": string;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    upload_api_v1_attachments__attachment_id__content_put: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    preview_job_api_v1_attachments__attachment_id__jobs_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PreviewJobInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentJobData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    preview_api_v1_attachments__attachment_id__preview_get: {
        parameters: {
            query: {
                page: number;
            };
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                    "image/png": string;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    initialize_api_v1_attachments_uploads_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UploadInit"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AuthData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    session_api_v1_auth_session_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AuthData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    chapters_api_v1_chapters_get: {
        parameters: {
            query: {
                archived?: boolean;
                cursor?: string | null;
                limit?: number;
                subject_id: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ChapterPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_chapter_api_v1_chapters_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateChapterInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ChapterData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    chapter_api_v1_chapters__chapter_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                chapter_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ChapterData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    patch_chapter_api_v1_chapters__chapter_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                chapter_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchChapterInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ChapterData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    day_summary_api_v1_day_summary_get: {
        parameters: {
            query?: {
                date?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_DaySummaryData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    live_api_v1_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_HealthData_"];
                };
            };
        };
    };
    ready_api_v1_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_HealthData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_home_api_v1_home_get: {
        parameters: {
            query?: {
                section?: ("quote" | "subjects" | "continue_learning" | "suggestions" | "methods" | "changes" | "review") | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_HomeData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_job_api_v1_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_AttachmentJobData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    points_api_v1_knowledge_points_get: {
        parameters: {
            query: {
                archived?: boolean;
                chapter_id: string;
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_KnowledgePointPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_point_api_v1_knowledge_points_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateKnowledgePointInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_KnowledgePointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    knowledge_point_evidence_api_v1_knowledge_points__knowledge_point_id__evidence_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                knowledge_point_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_KnowledgePointEvidenceData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    point_api_v1_knowledge_points__point_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                point_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_KnowledgePointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    patch_point_api_v1_knowledge_points__point_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                point_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchKnowledgePointInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_KnowledgePointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    learning_methods_api_v1_learning_methods_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_LearningMethodsData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    learning_method_api_v1_learning_methods__method_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                method_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_LearningMethodData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    session_history_api_v1_learning_sessions_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionHistoryData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    start_api_v1_learning_sessions_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateSessionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    session_detail_api_v1_learning_sessions__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    cancel_learning_session_api_v1_learning_sessions__session_id__cancel_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EndSessionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    end_api_v1_learning_sessions__session_id__end_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EndSessionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    pause_learning_session_api_v1_learning_sessions__session_id__pause_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EndSessionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    resume_learning_session_api_v1_learning_sessions__session_id__resume_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EndSessionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    correct_time_segment_api_v1_learning_sessions__session_id__time_segments__segment_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                segment_id: string;
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CorrectTimeSegmentInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SessionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    current_api_v1_learning_sessions_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_Union_SessionData__NoneType__"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    learning_situations_api_v1_learning_situations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_LearningSituationsData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    learning_situation_api_v1_learning_situations__situation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                situation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_LearningSituationData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_mastery_assessment_api_v1_mastery_assessments_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateMasteryAssessment"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_CreatedMasteryAssessmentData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    metadata_api_v1_meta_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProductMeta_"];
                };
            };
        };
    };
    create_attempt_api_v1_problem_attempts_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateAttempt"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttemptData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    attempt_api_v1_problem_attempts__attempt_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attempt_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttemptData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    update_attempt_api_v1_problem_attempts__attempt_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                attempt_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateAttempt"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttemptData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    list_items_api_v1_problem_comparisons_get: {
        parameters: {
            query?: {
                archived?: boolean | null;
                cursor?: string | null;
                limit?: number;
                problem_id?: string | null;
                subject_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ComparisonPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_api_v1_problem_comparisons_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateComparisonInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ComparisonData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_api_v1_problem_comparisons__comparison_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comparison_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ComparisonData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    patch_api_v1_problem_comparisons__comparison_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                comparison_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchComparisonInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ComparisonData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    problems_api_v1_problems_get: {
        parameters: {
            query?: {
                archived?: boolean;
                cursor?: string | null;
                limit?: number;
                representative?: boolean | null;
                subject_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_problem_api_v1_problems_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateProblem"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    problem_api_v1_problems__problem_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    update_problem_api_v1_problems__problem_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProblemPatchInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    problem_attachment_links_api_v1_problems__problem_id__attachment_links_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttachmentLinksData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    link_problem_attachment_api_v1_problems__problem_id__attachment_links_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LinkProblemAttachment"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttachmentLinkWriteData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    unlink_problem_attachment_api_v1_problems__problem_id__attachment_links__link_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                link_id: string;
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UnlinkProblemAttachment"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemAttachmentUnlinkData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    link_problem_api_v1_problems__problem_id__knowledge_links_put: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                problem_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProblemKnowledgeLinksInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ProblemKnowledgeLinksData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    update_preference_api_v1_quotes__quote_id__preference_put: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string;
                "If-Match"?: string | null;
                "If-None-Match"?: string | null;
            };
            path: {
                quote_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuotePreferenceInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_QuotePreferenceResultData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    favorites_api_v1_quotes_favorites_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_QuoteFavoritesData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    today_api_v1_quotes_today_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_QuoteTodayData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    records_api_v1_records_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                from?: string | null;
                limit?: number;
                subject_id?: string | null;
                to?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_RecordsPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_reflection_api_v1_session_reflections_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateReflection"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ReflectionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    reflection_api_v1_session_reflections__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ReflectionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    update_reflection_api_v1_session_reflections__session_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateReflection"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_ReflectionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    list_items_api_v1_stuck_points_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                knowledge_point_id?: string | null;
                limit?: number;
                session_id?: string | null;
                status?: ("open" | "resolved") | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_StuckPointPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_api_v1_stuck_points_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateStuckPointInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_StuckPointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    get_api_v1_stuck_points__stuck_point_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                stuck_point_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_StuckPointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    patch_api_v1_stuck_points__stuck_point_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                stuck_point_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchStuckPointInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_StuckPointData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    subjects_api_v1_subjects_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SubjectsData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    subject_space_api_v1_subjects__subject_id__space_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                subject_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SubjectSpaceData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    suggestions_api_v1_suggestions_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                kind?: string | null;
                limit?: number;
                status?: string;
                subject_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SuggestionPageData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    suggestion_api_v1_suggestions__suggestion_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                suggestion_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SuggestionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    action_api_v1_suggestions__suggestion_id__actions_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string;
                "if-match"?: string | null;
            };
            path: {
                suggestion_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SuggestionActionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope_SuggestionData_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
}
