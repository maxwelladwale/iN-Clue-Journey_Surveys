from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'
    
    session_type = fields.Selection([
        ('kickoff', 'KickOff Session'),
        ('followup1', 'FollowUp Session 1'),
        ('followup2', 'FollowUp Session 2'),
        ('followup3', 'FollowUp Session 3'),
        ('followup4', 'FollowUp Session 4'),
        ('followup5', 'FollowUp Session 5'),
        ('followup6', 'FollowUp Session 6'),
    ], string='Session Type',
    help="Specify what type of session this survey is for in the iN-Clue journey")
    
    participation_ids = fields.One2many(
        'inclue.participation',
        'survey_id',
        string='Participations'
    )
    
    is_inclue_survey = fields.Boolean(
        string='Is iN-Clue Survey',
        default=False,
        help="Check if this survey is part of the iN-Clue journey"
    )
    
    inclue_completion_rate = fields.Float(
        string='Completion Rate (%)',
        compute='_compute_inclue_stats',
        store=True
    )
    
    inclue_sent_count = fields.Integer(
        string='Sent Count',
        compute='_compute_inclue_stats',
        store=True
    )
    
    inclue_completed_count = fields.Integer(
        string='Completed Count',
        compute='_compute_inclue_stats',
        store=True
    )
    
    @api.depends('participation_ids', 'participation_ids.completed', 'participation_ids.survey_sent')
    def _compute_inclue_stats(self):
        for survey in self:
            sent = len(survey.participation_ids.filtered(lambda p: p.survey_sent))
            completed = len(survey.participation_ids.filtered(lambda p: p.completed))
            
            survey.inclue_sent_count = sent
            survey.inclue_completed_count = completed
            survey.inclue_completion_rate = (completed / sent * 100) if sent > 0 else 0.0

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    
    participation_id = fields.One2many(
        'inclue.participation',
        'user_input_id',
        string='Participation Record'
    )
    
    def _mark_done(self):
        """Override to update participation records when surveys are completed"""
        res = super(SurveyUserInput, self)._mark_done()
        
        # For each completed survey, update the corresponding participation
        for user_input in self:
            # Skip if already handled
            if user_input.state != 'done':
                continue
                
            # Try to find a participation record
            participation_model = self.env['inclue.participation']
            participation_model.process_survey_completion(user_input)
                
        return res