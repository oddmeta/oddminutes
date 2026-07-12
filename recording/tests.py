from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from recording.audio_recorder import AudioRecorder, get_recorder, reset_recorder
from meetings.models import Meeting


class AudioRecorderStatusTest(TestCase):
    def setUp(self):
        reset_recorder()

    def tearDown(self):
        reset_recorder()

    def test_start_when_not_recording(self):
        recorder = AudioRecorder()
        with patch('recording.audio_recorder.HAS_SOUNDDEVICE', False):
            result = recorder.start()
            self.assertFalse(result)
            self.assertEqual(recorder.status, 'error')

    def test_start_when_already_recording(self):
        recorder = AudioRecorder()
        recorder._recording = True
        recorder._status = 'recording'

        result = recorder.start()

        self.assertFalse(result)
        self.assertEqual(recorder.status, 'recording')
        self.assertEqual(recorder._error_message, 'Already recording')

    def test_start_when_paused(self):
        recorder = AudioRecorder()
        recorder._recording = True
        recorder._paused = True
        recorder._status = 'paused'

        result = recorder.start()

        self.assertFalse(result)
        self.assertEqual(recorder.status, 'recording')
        self.assertEqual(recorder._error_message, 'Already recording')

    def test_global_recorder_status_check(self):
        recorder = get_recorder()
        recorder._recording = True

        new_recorder = get_recorder()
        result = new_recorder.start()

        self.assertFalse(result)
        self.assertEqual(new_recorder._error_message, 'Already recording')


class StartRecordingAPITest(TestCase):
    def setUp(self):
        reset_recorder()
        self.client = Client()
        self.meeting = Meeting.objects.create(title='Test Meeting')

    def tearDown(self):
        reset_recorder()

    def test_start_recording_when_already_recording(self):
        recorder = get_recorder()
        recorder._recording = True
        recorder._status = 'recording'

        response = self.client.post(
            reverse('start_recording'),
            {'meeting_id': str(self.meeting.id)},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], '已经在录音中')