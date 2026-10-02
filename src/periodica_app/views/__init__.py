"""GPU views and the pure-Python controllers that drive them.

``camera_controller`` and ``frame_loop`` import no Kivy at module level
(tier-A testable); ``fbo_view`` needs a GL context to instantiate.
"""
