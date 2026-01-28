import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './Footer.css'

function Footer() {
  const { t } = useTranslation()
  
  return (
    <footer className="footer">
      <div className="footer-main">
        <div className="footer-container">
          <motion.div 
            className="footer-column"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h3 className="footer-heading">Co-Code GGW</h3>
            <p className="footer-text">
              {t('footer.description')}
            </p>
          </motion.div>

          <motion.div 
            className="footer-column"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.6 }}
          >
            <h3 className="footer-heading">{t('footer.product.title')}</h3>
            <a href="#features" className="footer-link">{t('header.nav.features')}</a>
            <a href="#how-it-works" className="footer-link">{t('header.nav.howItWorks')}</a>
            <a href="#privacy" className="footer-link">{t('header.nav.privacySecurity')}</a>
            <a href="#faq" className="footer-link">{t('header.nav.faq')}</a>
            <a href="#contact" className="footer-link">{t('header.nav.contact')}</a>
          </motion.div>

          <motion.div 
            className="footer-column footer-cta"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.6 }}
          >
            <div className="footer-logo">
              <span className="footer-logo-main">Co-Code</span>
              <span className="footer-logo-sub">GGW</span>
            </div>
            <h3 className="footer-cta-text">
              {t('footer.cta.title')}
            </h3>
            <div className="footer-buttons">
              <motion.a 
                href="#contact" 
                className="footer-btn footer-btn-outline"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {t('footer.cta.contact')}
              </motion.a>
              <motion.a 
                href="#demo" 
                className="footer-btn footer-btn-solid"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {t('footer.cta.demo')}
              </motion.a>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="footer-bottom-container">
          <nav className="footer-nav">
            <a href="#features" className="footer-nav-link">{t('header.nav.features')}</a>
            <a href="#privacy" className="footer-nav-link">{t('footer.bottom.privacy')}</a>
            <a href="#terms" className="footer-nav-link">{t('footer.bottom.terms')}</a>
            <a href="#contact" className="footer-nav-link">{t('header.nav.contact')}</a>
          </nav>
          <div className="footer-copyright">
            <p>{t('footer.bottom.copyright')}</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
