{
    'name': 'iN-Clue Journey Event Survey 20',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Link events with surveys for the iN-Clue Journey experience',
    'description': """
        This module enables linking of events to surveys.
        It tracks participant sessions (kickoff & follow-up) to allow later
        analysis and automated follow-ups.
        
        Features:
        - Link events to surveys
        - Track participant journey across multiple sessions
        - Automated survey distribution
        - Dashboard for journey analytics
        - Portal access for participants
    """,
    'author': 'Your Name or Company',
    'depends': ['base', 'event', 'survey', 'mail', 'portal', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/survey_templates.xml',
        'views/event_form.xml',
        'views/participation_tracking.xml',
        'views/survey_form.xml',
        # 'views/inclue_dashboard.xml',
        # 'views/portal_templates.xml',
        'data/email_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inclueyoh/static/src/js/inclue_dashboard.js',
            'inclueyoh/static/src/scss/inclue_style.scss',
        ],
    },
    'installable': True,
    'application': True,
}