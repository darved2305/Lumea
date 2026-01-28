import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './Testimonials.css'

function Testimonials() {
  const { t } = useTranslation()
  const [currentIndex, setCurrentIndex] = useState(0)

  const articles = [
    {
      title: t('news.articles.abha.title'),
      source: t('news.articles.abha.source'),
      date: '14 Oct 2024',
      snippet: t('news.articles.abha.snippet'),
      link: 'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=2064531'
    },
    {
      title: t('news.articles.nppa.title'),
      source: t('news.articles.nppa.source'),
      date: '9 Dec 2025',
      snippet: t('news.articles.nppa.snippet'),
      link: 'https://pib.gov.in/PressReleasePage.aspx?PRID=2087562'
    },
    {
      title: t('news.articles.ocr.title'),
      source: t('news.articles.ocr.source'),
      date: '12 Dec 2024',
      snippet: t('news.articles.ocr.snippet'),
      link: 'https://www.healthcareittoday.com/2024/12/12/ocr-transforms-healthcare-document-management/'
    }
  ]

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? articles.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setCurrentIndex((prev) => (prev === articles.length - 1 ? 0 : prev + 1))
  }

  return (
    <section className="testimonials">
      <div className="testimonials-container">
          <div className="testimonial-content">
          <motion.p 
            className="testimonial-label"
            initial={{ opacity: 0, y: -20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            {t('news.label')}
          </motion.p>

          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ duration: 0.5 }}
            >
              <h2 className="article-title">
                {articles[currentIndex].title}
              </h2>

              <div className="article-meta">
                <span className="article-source">{articles[currentIndex].source}</span>
                <span className="article-divider">•</span>
                <span className="article-date">{articles[currentIndex].date}</span>
              </div>

              <p className="article-snippet">
                {articles[currentIndex].snippet}
              </p>

              <a 
                href={articles[currentIndex].link} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="article-link"
              >
                {t('news.readMore')} →
              </a>
            </motion.div>
          </AnimatePresence>

          <div className="testimonial-controls">
            <button 
              className="control-btn prev-btn" 
              onClick={handlePrevious}
              aria-label="Previous article"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M12 4L6 10L12 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <button 
              className="control-btn next-btn" 
              onClick={handleNext}
              aria-label="Next article"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M8 4L14 10L8 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Testimonials
