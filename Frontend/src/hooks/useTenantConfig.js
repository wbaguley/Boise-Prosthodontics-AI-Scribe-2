import { useState, useEffect } from 'react';

/**
 * React hook for loading and using tenant configuration
 * Fetches tenant-specific branding, features, and settings
 * 
 * @returns {Object} - { config, loading, error }
 */
const useTenantConfig = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTenantConfig = async () => {
      try:
        setLoading(true);
        setError(null);

        const response = await fetch('/api/config');
        
        if (!response.ok) {
          throw new Error(`Failed to load tenant configuration: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (data.tenant && data.tenant.success) {
          const tenantConfig = {
            tenant_id: data.tenant.tenant_id || 'default',
            practice_name: data.tenant.practice_name || 'Dental Practice',
            logo_url: data.tenant.logo_url || '',
            primary_color: data.tenant.primary_color || '#3B82F6',
            secondary_color: data.tenant.secondary_color || '#8B5CF6',
            features_enabled: data.tenant.features_enabled || {},
            llm_provider: data.tenant.llm_provider || 'ollama',
            whisper_model: data.tenant.whisper_model || 'medium'
          };

          setConfig(tenantConfig);

          // Apply CSS custom properties for tenant colors
          if (tenantConfig.primary_color) {
            document.documentElement.style.setProperty('--primary-color', tenantConfig.primary_color);
          }
          if (tenantConfig.secondary_color) {
            document.documentElement.style.setProperty('--secondary-color', tenantConfig.secondary_color);
          }

          // Update document title with practice name
          if (tenantConfig.practice_name) {
            document.title = `${tenantConfig.practice_name} - AI Scribe`;
          }

          console.log('✅ Tenant configuration loaded:', tenantConfig.tenant_id);
        } else {
          throw new Error('Invalid tenant configuration response');
        }
      } catch (err) {
        console.error('Error loading tenant configuration:', err);
        setError(err.message);
        
        // Set default config on error
        setConfig({
          tenant_id: 'default',
          practice_name: 'Dental Practice',
          logo_url: '',
          primary_color: '#3B82F6',
          secondary_color: '#8B5CF6',
          features_enabled: {
            ambient_scribe: true,
            dentrix_integration: true,
            voice_profiles: true,
            openai_option: true,
            email_system: true,
            soap_templates: true
          },
          llm_provider: 'ollama',
          whisper_model: 'medium'
        });
      } finally {
        setLoading(false);
      }
    };

    loadTenantConfig();
  }, []);

  return { config, loading, error };
};

export default useTenantConfig;
