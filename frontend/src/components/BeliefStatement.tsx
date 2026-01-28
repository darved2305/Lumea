import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './BeliefStatement.css'

function BeliefStatement() {
  const { t } = useTranslation()
  
  return (
    <section className="belief-statement">
      <div className="belief-container">
        <motion.div 
          className="leaf-icon"
          initial={{ opacity: 0, scale: 0.5 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, type: 'spring', stiffness: 150 }}
        >
          <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
            <path d="M35 5 Q50 20 35 35 Q20 20 35 5 Z" fill="#7ba88a" />
            <path d="M65 35 Q50 50 35 35 Q50 20 65 35 Z" fill="#7ba88a" />
            <path d="M35 65 Q20 50 35 35 Q50 50 35 65 Z" fill="#7ba88a" />
            <path d="M5 35 Q20 20 35 35 Q20 50 5 35 Z" fill="#7ba88a" />
          </svg>
        </motion.div>

        <motion.p 
          className="belief-text"
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 1 }}
        >
          {t('belief.message')}
        </motion.p>

        <motion.p 
          className="belief-subtext"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6, duration: 0.8 }}
        >
          {t('belief.tagline')}
        </motion.p>
      </div>
    </section>
  )
}

export default BeliefStatement
