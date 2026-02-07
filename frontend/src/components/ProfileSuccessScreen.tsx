/**
 * Profile Success Screen Component
 * 
 * GPay-like success animation shown after health profile form submission.
 * Features animated checkmark, success message, and navigation options.
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, ArrowRight } from 'lucide-react';
import './ProfileSuccessScreen.css';

interface ProfileSuccessScreenProps {
  autoRedirect?: boolean;
  redirectDelay?: number;
}

export default function ProfileSuccessScreen({
  autoRedirect = true,
  redirectDelay = 2000
}: ProfileSuccessScreenProps) {
  const navigate = useNavigate();

  useEffect(() => {
    // Profile sync is now handled by the Features page which shows a
    // live sync overlay.  We just redirect there after the success animation.
    if (autoRedirect) {
      const timer = setTimeout(() => {
        navigate('/features', { state: { fromProfileSync: true } });
      }, redirectDelay);

      return () => clearTimeout(timer);
    }
  }, [autoRedirect, redirectDelay, navigate]);

  const handleFeatures = () => {
    navigate('/features', { state: { fromProfileSync: true } });
  };

  const handleSettings = () => {
    navigate('/settings');
  };

  return (
    <motion.div
      className="profile-success-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        className="profile-success-container"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{
          type: "spring",
          stiffness: 200,
          damping: 20,
          delay: 0.1
        }}
      >
        {/* Animated Checkmark */}
        <motion.div
          className="success-checkmark-container"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 15,
            delay: 0.2
          }}
        >
          <motion.div
            className="success-checkmark-circle"
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.5 }}
            >
              <Check size={48} strokeWidth={3} />
            </motion.div>
          </motion.div>

          {/* Ripple effect */}
          <motion.div
            className="success-ripple"
            initial={{ scale: 0.8, opacity: 0.8 }}
            animate={{ scale: 2, opacity: 0 }}
            transition={{ duration: 1, delay: 0.3 }}
          />
        </motion.div>

        {/* Success Message */}
        <motion.div
          className="success-message"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
        >
          <h2 className="success-title">Saved!</h2>
          <p className="success-description">
            Your health profile has been updated.
          </p>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          className="success-actions"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.4 }}
        >
          <button
            className="success-btn success-btn-primary"
            onClick={handleFeatures}
          >
            View Health Intelligence
            <ArrowRight size={18} />
          </button>
          <button
            className="success-btn success-btn-secondary"
            onClick={handleSettings}
          >
            Edit in Settings
          </button>
        </motion.div>

        {/* Auto-redirect indicator */}
        {autoRedirect && (
          <motion.p
            className="success-auto-redirect"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1, duration: 0.3 }}
          >
            Redirecting to Health Intelligence...
          </motion.p>
        )}
      </motion.div>
    </motion.div>
  );
}
