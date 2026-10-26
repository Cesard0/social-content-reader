import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from content_eval.common import read, write
from content_eval.reader import identify, prepare, transcribe
from content_eval.evidence import retrieve


class ReaderTests(unittest.TestCase):
    def test_variants_reuse_canonical_content_id(self):
        self.assertEqual(identify('https://youtu.be/jNQXAC9IVRw?si=tracking')[2],
                         identify('https://www.youtube.com/shorts/jNQXAC9IVRw')[2])
        self.assertEqual(identify('https://twitter.com/person/status/123?s=20')[2],
                         identify('https://x.com/person/status/123')[2])
        self.assertEqual(identify('https://instagram.com/reel/ABC/?igsh=tracking')[2],
                         identify('https://www.instagram.com/p/ABC/')[2])
        with self.assertRaises(ValueError):
            identify('https://youtube.com.evil.test/watch?v=jNQXAC9IVRw')

    def test_image_carousel_does_not_require_video_and_cache_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            def retrieve(url, folder):
                (folder / 'one.jpg').write_bytes(b'image fixture')
                write(folder / 'post-context.json', {'text': 'A carousel caption'})
                return 'carousel'
            with patch('content_eval.reader.instagram', side_effect=retrieve) as adapter, patch('content_eval.reader.collect') as collector:
                result, path = prepare('https://instagram.com/p/ABC/', tmp, Path('missing'))
                self.assertEqual(result['content_type'], 'carousel')
                self.assertEqual(len(result['images']), 1)
                collector.assert_not_called()
                cached, _ = prepare('https://instagram.com/reel/ABC/?igsh=tracking', tmp, Path('missing'))
                self.assertEqual(cached, result)
                self.assertEqual(adapter.call_count, 1)
                Path(result['images'][0]).write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'modified'):
                    prepare('https://instagram.com/p/ABC/', tmp, Path('missing'))

    def test_subtitles_precede_asr_and_missing_speech_is_explicit(self):
        record = {'transcript': {'status': 'success', 'paths': ['source.en.vtt']},
                  'audio': {'status': 'success', 'path': 'audio.wav'}}
        with patch('content_eval.reader.run') as runner:
            result = transcribe(record, Path('/tmp'), Path('/missing'))
            self.assertEqual(result['status'], 'subtitles')
            runner.assert_not_called()
        record['transcript'] = {'status': 'unavailable'}
        result = transcribe(record, Path('/tmp'), Path('/missing'))
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('Missing', result['reason'])

    def test_subtitle_error_keeps_downloaded_media_and_partial_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            def adapter(command, *args):
                self.assertIn('--ignore-errors', command)
                (folder / 'source.mp4').write_bytes(b'media fixture')
                return {'returncode': 0, 'stdout': '', 'stderr': 'ERROR: subtitle HTTP 429'}
            with patch('content_eval.evidence.shutil.which', return_value='/tool/yt-dlp'), patch('content_eval.evidence.run', side_effect=adapter):
                media, _, status = retrieve({'url': 'https://example.test/video'}, folder)
                self.assertTrue(media.is_file())
                self.assertEqual(status['status'], 'partial')
                self.assertIn('429', status['reason'])

    def test_failed_video_retrieval_is_saved_and_reused(self):
        record = {'id': 'video', 'retrieval': {'status': 'failed', 'reason': 'login wall'},
                  'audio': {'status': 'unavailable'}, 'transcript': {'status': 'unavailable'}}
        with tempfile.TemporaryDirectory() as tmp, patch('content_eval.reader.collect', return_value={'items': [record]}) as collector:
            result, path = prepare('https://x.com/person/status/123', tmp, Path('missing'))
            self.assertEqual(result['videos'][0]['retrieval']['status'], 'failed')
            self.assertEqual(read(path), result)
            prepare('https://twitter.com/person/status/123', tmp, Path('missing'))
            self.assertEqual(collector.call_count, 1)

    def test_refresh_preserves_previous_and_becomes_default_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            def retrieve(url, folder):
                (folder / 'one.jpg').write_bytes(b'image')
                return 'image'
            with patch('content_eval.reader.instagram', side_effect=retrieve) as adapter:
                _, original = prepare('https://instagram.com/p/ABC/', tmp, Path('missing'))
                refreshed, newer = prepare('https://instagram.com/p/ABC/', tmp, Path('missing'), refresh=True)
                cached, current = prepare('https://instagram.com/p/ABC/', tmp, Path('missing'))
                self.assertNotEqual(original, newer)
                self.assertTrue(original.exists())
                self.assertEqual(current, newer)
                self.assertEqual(cached, refreshed)
                self.assertEqual(adapter.call_count, 2)


if __name__ == '__main__':
    unittest.main()
