from django.test import TestCase
from rest_framework import status


class OpenApiDocumentationTests(TestCase):
    def setUp(self):
        self.client.defaults['HTTP_ACCEPT'] = 'application/json'

    def test_schema_is_accessible_and_describes_authentication_endpoints(self):
        response = self.client.get('/api/schema/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = response.json()
        self.assertEqual(schema['openapi'], '3.0.3')
        self.assertEqual(schema['info']['title'], 'Portfolio CMS API')
        self.assertIn('/api/auth/token/', schema['paths'])
        self.assertIn('/api/auth/token/refresh/', schema['paths'])

    def test_schema_declares_bearer_jwt_authentication(self):
        response = self.client.get('/api/schema/')
        schema = response.json()

        self.assertEqual(
            schema['components']['securitySchemes']['jwtAuth'],
            {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'},
        )

    def test_schema_documents_public_and_staff_content_routes(self):
        schema = self.client.get('/api/schema/').json()

        self.assertIn('/api/public/profile/', schema['paths'])
        self.assertIn('/api/public/projects/', schema['paths'])
        self.assertIn('/api/public/contact/', schema['paths'])
        self.assertIn('/api/cms/projects/', schema['paths'])
        self.assertIn('post', schema['paths']['/api/cms/projects/{id}/publish/'])
        self.assertIn('get', schema['paths']['/api/cms/projects/{id}/preview/'])
        self.assertNotIn('/api/public/media/', schema['paths'])
        public_security = schema['paths']['/api/public/projects/']['get']['security']
        cms_security = schema['paths']['/api/cms/projects/']['get']['security']
        self.assertIn({}, public_security)
        self.assertTrue(any('jwtAuth' in requirement for requirement in cms_security))

    def test_swagger_and_redoc_pages_are_accessible(self):
        swagger = self.client.get('/api/docs/swagger/', HTTP_ACCEPT='text/html')
        redoc = self.client.get('/api/docs/redoc/', HTTP_ACCEPT='text/html')

        self.assertEqual(swagger.status_code, status.HTTP_200_OK)
        self.assertContains(swagger, 'id="swagger-ui"')
        self.assertContains(swagger, '"/api/schema/"')
        self.assertEqual(redoc.status_code, status.HTTP_200_OK)
        self.assertContains(redoc, '<redoc')
        self.assertContains(redoc, '/api/schema/')
