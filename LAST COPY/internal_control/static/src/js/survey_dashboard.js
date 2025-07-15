/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const actionRegistry = registry.category("actions");

export class SurveyDashboard extends Component {
    static template = 'SurveyDashboard';


    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            surveys: [],
            selectedSurvey: null,
            selectedResponse: null,
            category_type: null,
            summaryData: {
                total_surveys: 0,
                total_responses: 0,
                average_score: 0,
                response_rate: 0,
                category_distribution: {},
                campaign_stats: [],
                total_campaigns: 0
            },
            detailedData: {
                responses: [],
                metrics: {},
                sections: {},
            },
            currentView: 'summary',
            loading: false,
            filters: {
                survey_id: null,
            },
                    // Nuevas propiedades para herramientas
        showTools: false,
        selectedSurveyForExport: null,
        showImportWizard: false,
        selectedFile: null,
        selectedFileName: ''
        });

        onWillStart(async () => {
            await this.loadInitialData();
        });
    }



    async loadInitialData() {
        try {
            this.state.loading = true;
            
            // Construir el dominio de búsqueda
            const domain = [["state", "=", "done"]];
            
            if (this.state.filters.survey_id) {
                domain.push(["survey_id", "=", this.state.filters.survey_id]);
            }
            
            // Obtener encuestas
            const surveys = await this.orm.searchRead(
                "survey.survey",
                [["active", "=", true]],
                ["id", "title", "category_id", "create_date", "user_input_ids"]
            );

            // Obtener respuestas
            const responses = await this.orm.searchRead(
                "survey.user_input",
                domain,
                ["id", "survey_id", "partner_id", "create_date", "scoring_percentage", "department_id", "campaign_id"]
            );

            // Obtener campañas con asignaciones
            const campaigns = await this.orm.searchRead(
                "in.survey.campaign",
                [],
                ["id", "name", "assignment_ids"]
            );
            // Obtener todas las asignaciones de campañas
            const allAssignments = await this.orm.searchRead(
                "in.survey.campaign.assignment",
                [],
                ["id", "campaign_id"]
            );
            // Agrupar asignaciones por campaña
            const assignmentsByCampaign = {};
            allAssignments.forEach(a => {
                if (!assignmentsByCampaign[a.campaign_id[0]]) assignmentsByCampaign[a.campaign_id[0]] = [];
                assignmentsByCampaign[a.campaign_id[0]].push(a.id);
            });
            // Agrupar respuestas por campaña
            const responsesByCampaign = {};
            responses.forEach(r => {
                if (r.campaign_id) {
                    const cid = r.campaign_id[0];
                    if (!responsesByCampaign[cid]) responsesByCampaign[cid] = [];
                    responsesByCampaign[cid].push(r.id);
                }
            });
            // Estadísticas por campaña
            const campaignStats = campaigns.map(campaign => {
                const total_esperados = (assignmentsByCampaign[campaign.id] || []).length;
                const total_respuestas = (responsesByCampaign[campaign.id] || []).length;
                const porcentaje_cumplimiento = total_esperados > 0 ? (total_respuestas / total_esperados) * 100 : 0;
                return {
                    id: campaign.id,
                    name: campaign.name,
                    total_esperados: total_esperados,
                    total_respuestas: total_respuestas,
                    porcentaje_cumplimiento: porcentaje_cumplimiento
                };
            });

            // Obtenemos las métricas calculadas
            const metrics = await this.orm.searchRead(
                "survey.calculate.report",
                [["user_input_id", "in", responses.map(r => r.id)]],
                ["id", "user_input_id", "category_id", "calculated_date"]
            );

            // Procesamos los datos
            const surveyData = surveys.map(survey => {
                const surveyResponses = responses.filter(r => r.survey_id[0] === survey.id);
                const surveyMetrics = metrics.filter(m => 
                    surveyResponses.some(r => r.id === m.user_input_id)
                );

                return {
                    id: survey.id,
                    title: survey.title,
                    category: survey.category_id ? survey.category_id[1] : 'Sin categoría',
                    category_id: survey.category_id ? survey.category_id[0] : false,
                    total_responses: surveyResponses.length,
                    metrics: surveyMetrics
                };
            });

            this.state.surveys = surveyData;
            this.state.summaryData = {
                total_surveys: surveys.length,
                total_responses: responses.length,
                average_score: 0,
                response_rate: surveys.length > 0 ? responses.length / surveys.length : 0,
                category_distribution: this.calculateCategoryDistribution(surveyData),
                campaign_stats: campaignStats,
                total_campaigns: campaigns.length
            };

        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add(
                "Error al cargar los datos del dashboard",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    calculateCategoryDistribution(surveyData) {
        const distribution = {};
        surveyData.forEach(survey => {
            if (!distribution[survey.category]) {
                distribution[survey.category] = {
                    total_responses: 0,
                    percentage: 0,
                    average_score: 0,
                    total_items_revisados: 0,
                    total_items_sin_novedad: 0,
                    porcentaje_cumplimiento: 0
                };
            }
            distribution[survey.category].total_responses += survey.total_responses;
        });

        // Calcular porcentajes
        Object.keys(distribution).forEach(category => {
            const data = distribution[category];
            data.percentage = this.state.summaryData.total_responses > 0 
                ? data.total_responses / this.state.summaryData.total_responses 
                : 0;
        });

        return distribution;
    }

    async loadSurveyDetails(surveyId) {
        try {
            this.state.loading = true;
            
            // Validar que surveyId sea válido
            if (!surveyId || isNaN(surveyId)) {
                console.warn("SurveyId inválido:", surveyId);
                this.state.currentView = 'summary';
                this.state.selectedSurvey = null;
                await this.loadInitialData();
                return;
            }
            
            // Obtenemos los detalles de la encuesta
            const survey = await this.orm.read(
                "survey.survey",
                [surveyId],
                ["id", "title", "category_id", "user_input_ids"]
            );
            console.log("1. Detalles de la encuesta:", survey);

            // Obtenemos las respuestas
            const responses = await this.orm.searchRead(
                "survey.user_input",
                [["survey_id", "=", surveyId], ["state", "=", "done"]],
                ["id", "partner_id", "create_date", "scoring_percentage"]
            );
            console.log("2. Respuestas encontradas:", responses);

            // Obtenemos los reportes de cálculo
            const calculateReports = await this.orm.searchRead(
                "survey.calculate.report",
                [["user_input_id", "in", responses.map(r => r.id)]],
                ["id", "user_input_id", "category_id", "calculated_date"]
            );
            console.log("3. Reportes de cálculo:", calculateReports);

            // Determinamos la categoría basada en el primer reporte
            const firstReport = calculateReports[0];
            const category = firstReport ? firstReport.category_id[1] : null;
            console.log("4. Categoría determinada:", category);

            // Procesamos los datos según la categoría
            const responseData = await Promise.all(responses.map(async response => {
                const report = calculateReports.find(r => r.user_input_id && r.user_input_id[0] === response.id);
                console.log(`5. Reporte para respuesta ${response.id}:`, report);

                let metrics = {};
                let totalMetrics = {};

                if (report) {
                    console.log("5.1 Categoría del reporte:", report.category_id[1]);
                    if (report.category_id[1] === 'revision_items') {
                        // Obtener métricas de items revisados
                        const revisedItems = await this.orm.searchRead(
                            "survey.revised.items",
                            [["calculate_report_id", "=", report.id]],
                            ["page_id", "page_name", "total_items_revisados", 
                             "total_items_sin_novedad", "porcentaje_cumplimiento"]
                        );
                        
                        metrics = revisedItems.reduce((acc, item) => {
                            acc[item.page_id[0]] = {
                                name: item.page_name,
                                total_items_revisados: item.total_items_revisados,
                                total_items_sin_novedad: item.total_items_sin_novedad,
                                porcentaje_cumplimiento: item.porcentaje_cumplimiento
                            };
                            return acc;
                        }, {});

                        // Calcular totales
                        totalMetrics = {
                            total_items_revisados: revisedItems.reduce((sum, item) => sum + item.total_items_revisados, 0),
                            total_items_sin_novedad: revisedItems.reduce((sum, item) => sum + item.total_items_sin_novedad, 0),
                            porcentaje_cumplimiento: revisedItems.length > 0 
                                ? revisedItems.reduce((sum, item) => sum + item.porcentaje_cumplimiento, 0) / revisedItems.length 
                                : 0
                        };
                    } else if (report.category_id[1] === 'compliance') {
                        // Obtener métricas de compliance
                        const complianceItems = await this.orm.searchRead(
                            "survey.compliance",
                            [["calculate_report_id", "=", report.id]],
                            ["page_id", "page_name", "compliance_status", "observations"]
                        );
                        
                        metrics = complianceItems.reduce((acc, item) => {
                            acc[item.page_id[0]] = {
                                name: item.page_name,
                                compliance_status: item.compliance_status,
                                observations: item.observations
                            };
                            return acc;
                        }, {});

                        // Calcular totales
                        totalMetrics = {
                            total_cumple: complianceItems.filter(item => item.compliance_status === 'cumple').length,
                            total_no_cumple: complianceItems.filter(item => item.compliance_status === 'no_cumple').length,
                            total_na: complianceItems.filter(item => item.compliance_status === 'na').length,
                            total_items: complianceItems.length
                        };

                        // Calcular porcentajes
                        if (totalMetrics.total_items > 0) {
                            totalMetrics.porcentaje_cumple = (totalMetrics.total_cumple / totalMetrics.total_items) * 100;
                            totalMetrics.porcentaje_no_cumple = (totalMetrics.total_no_cumple / totalMetrics.total_items) * 100;
                            totalMetrics.porcentaje_na = (totalMetrics.total_na / totalMetrics.total_items) * 100;
                        }
                    } else if (report.category_id[1] === 'satisfaction') {
                        // Obtener métricas de satisfacción
                        const satisfactionItems = await this.orm.searchRead(
                            "survey.satisfaction",
                            [["calculate_report_id", "=", report.id]],
                            ["page_id", "page_name", "satisfaccion", "porcentaje_satisfaccion"]
                        );
                        metrics = satisfactionItems.reduce((acc, item) => {
                            acc[item.page_id[0]] = {
                                name: item.page_name,
                                satisfaccion: item.satisfaccion,
                                porcentaje_satisfaccion: item.porcentaje_satisfaccion
                            };
                            return acc;
                        }, {});
                        totalMetrics = {
                            promedio_satisfaccion: satisfactionItems.length > 0
                                ? satisfactionItems.reduce((sum, item) => sum + item.porcentaje_satisfaccion, 0) / satisfactionItems.length
                                : 0
                        };
                    } else if (report.category_id[1] === 'participation') {
                        // Obtener métricas de participación
                        const participationItems = await this.orm.searchRead(
                            "survey.participation",
                            [["calculate_report_id", "=", report.id]],
                            ["page_id", "page_name", "respuestas_si", "respuestas_no", "no_respondieron", "porcentaje_participacion"]
                        );
                        metrics = participationItems.reduce((acc, item) => {
                            acc[item.page_id[0]] = {
                                name: item.page_name,
                                respuestas_si: item.respuestas_si,
                                respuestas_no: item.respuestas_no,
                                no_respondieron: item.no_respondieron,
                                porcentaje_participacion: item.porcentaje_participacion
                            };
                            return acc;
                        }, {});
                        totalMetrics = {
                            promedio_participacion: participationItems.length > 0
                                ? participationItems.reduce((sum, item) => sum + item.porcentaje_participacion, 0) / participationItems.length
                                : 0
                        };
                    }
                }

                return {
                    id: response.id,
                    respondent_name: response.partner_id ? response.partner_id[1] : 'Anónimo',
                    date: response.create_date,
                    score: response.scoring_percentage,
                    metrics: metrics,
                    total_metrics: totalMetrics,
                    category: report ? report.category_id[1] : null
                };
            }));

            this.state.selectedSurvey = {
                id: survey.id,
                title: survey.title,
                category: category || 'Sin categoría',
                category_id: firstReport ? firstReport.category_id[0] : false
            };

            this.state.category_type = category;
            console.log("6. Estado actualizado:", {
                selectedSurvey: this.state.selectedSurvey,
                category_type: this.state.category_type
            });

            this.state.detailedData = {
                responses: responseData,
                metrics: this.calculateSurveyMetrics(responseData)
            };

            console.log("6. Datos finales procesados:", this.state.detailedData);

            this.state.currentView = 'detailed';
        } catch (error) {
            console.error("Error loading survey details:", error);
            this.notification.add(
                "Error al cargar los detalles de la encuesta",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    calculateSurveyMetrics(responses) {
        if (!responses.length) return {};

        // Determinar la categoría basada en la primera respuesta
        const category = responses[0].category;
        const metrics = {
            total_responses: responses.length
        };

        if (category === 'revision_items') {
            metrics.total_items_revisados = 0;
            metrics.total_items_sin_novedad = 0;
            metrics.porcentaje_cumplimiento = 0;

            responses.forEach(response => {
                Object.values(response.metrics).forEach(section => {
                    metrics.total_items_revisados += section.total_items_revisados || 0;
                    metrics.total_items_sin_novedad += section.total_items_sin_novedad || 0;
                });
            });

            if (metrics.total_items_revisados > 0) {
                metrics.porcentaje_cumplimiento = (metrics.total_items_sin_novedad / metrics.total_items_revisados) * 100;
            }
        } else if (category === 'compliance') {
            metrics.total_cumple = 0;
            metrics.total_no_cumple = 0;
            metrics.total_na = 0;
            metrics.total_items = 0;

            responses.forEach(response => {
                Object.values(response.metrics).forEach(section => {
                    metrics.total_items++;
                    if (section.compliance_status === 'cumple') {
                        metrics.total_cumple++;
                    } else if (section.compliance_status === 'no_cumple') {
                        metrics.total_no_cumple++;
                    } else if (section.compliance_status === 'na') {
                        metrics.total_na++;
                    }
                });
            });

            // Calcular porcentajes
            if (metrics.total_items > 0) {
                metrics.porcentaje_cumple = (metrics.total_cumple / metrics.total_items) * 100;
                metrics.porcentaje_no_cumple = (metrics.total_no_cumple / metrics.total_items) * 100;
                metrics.porcentaje_na = (metrics.total_na / metrics.total_items) * 100;
            }
        } else if (category === 'satisfaction') {
            metrics.total_satisfaccion = 0;
            metrics.promedio_satisfaccion = 0;
            metrics.promedio_porcentaje_satisfaccion = 0;
            let count = 0;
            responses.forEach(response => {
                Object.values(response.metrics).forEach(section => {
                    metrics.total_satisfaccion += section.satisfaccion || 0;
                    metrics.promedio_porcentaje_satisfaccion += section.porcentaje_satisfaccion || 0;
                    count++;
                });
            });
            if (count > 0) {
                metrics.promedio_satisfaccion = metrics.total_satisfaccion / count;
                metrics.promedio_porcentaje_satisfaccion = metrics.promedio_porcentaje_satisfaccion / count;
            }
        } else if (category === 'participation') {
            metrics.total_si = 0;
            metrics.total_no = 0;
            metrics.total_no_respondieron = 0;
            metrics.promedio_participacion = 0;
            let count = 0;
            responses.forEach(response => {
                Object.values(response.metrics).forEach(section => {
                    metrics.total_si += section.respuestas_si || 0;
                    metrics.total_no += section.respuestas_no || 0;
                    metrics.total_no_respondieron += section.no_respondieron || 0;
                    metrics.promedio_participacion += section.porcentaje_participacion || 0;
                    count++;
                });
            });
            if (count > 0) {
                metrics.promedio_participacion = metrics.promedio_participacion / count;
            }
        }

        return metrics;
    }



    onSurveySelect(ev) {
        const surveyId = parseInt(ev.target.value) || null;
        if (surveyId && !isNaN(surveyId)) {
            this.state.filters.survey_id = surveyId;
            this.loadSurveyDetails(surveyId);
        } else {
            this.state.filters.survey_id = null;
            this.state.currentView = 'summary';
            this.state.selectedSurvey = null;
            this.state.selectedResponse = null;
            this.loadInitialData();
        }
    }

    onResponseSelect(responseId) {
        this.state.selectedResponse = this.state.detailedData.responses.find(r => r.id === responseId);
    }

    formatNumber(value) {
        if (value === undefined || value === null) return '0';
        return value.toLocaleString();
    }

    formatPercentage(value) {
        if (value === undefined || value === null) return '0%';
        return `${(value * 100).toFixed(2)}%`;
    }

    getCategoryDisplayInfo(category) {
        const categoryInfo = {
            'revision_items': {
                name: 'Items Revisados',
                icon: 'fa fa-search'
            },
            'compliance': {
                name: 'Cumplimiento',
                icon: 'fa fa-check-circle'
            },
            'satisfaction': {
                name: 'Satisfacción',
                icon: 'fa fa-smile-o'
            },
            'participation': {
                name: 'Participación',
                icon: 'fa fa-users'
            },
            'quality': {
                name: 'Calidad',
                icon: 'fa fa-star'
            },
            'efficiency': {
                name: 'Eficiencia',
                icon: 'fa fa-bolt'
            },
            'safety': {
                name: 'Seguridad',
                icon: 'fa fa-shield'
            },
            'training': {
                name: 'Capacitación',
                icon: 'fa fa-graduation-cap'
            },
            'communication': {
                name: 'Comunicación',
                icon: 'fa fa-comments'
            },
            'leadership': {
                name: 'Liderazgo',
                icon: 'fa fa-crown'
            },
            'teamwork': {
                name: 'Trabajo en Equipo',
                icon: 'fa fa-handshake-o'
            },
            'innovation': {
                name: 'Innovación',
                icon: 'fa fa-lightbulb-o'
            },
            'customer_service': {
                name: 'Servicio al Cliente',
                icon: 'fa fa-headphones'
            },
            'process_improvement': {
                name: 'Mejora de Procesos',
                icon: 'fa fa-line-chart'
            },
            'risk_management': {
                name: 'Gestión de Riesgos',
                icon: 'fa fa-exclamation-triangle'
            }
        };
        
        return categoryInfo[category] || {
            name: category,
            icon: 'fa fa-list'
        };
    }

    getCategoryDisplayName(category) {
        const categoryNames = {
            'revision_items': 'Items Revisados',
            'compliance': 'Cumplimiento',
            'satisfaction': 'Satisfacción',
            'participation': 'Participación',
            'quality': 'Calidad',
            'efficiency': 'Eficiencia',
            'safety': 'Seguridad',
            'training': 'Capacitación',
            'communication': 'Comunicación',
            'leadership': 'Liderazgo',
            'teamwork': 'Trabajo en Equipo',
            'innovation': 'Innovación',
            'customer_service': 'Servicio al Cliente',
            'process_improvement': 'Mejora de Procesos',
            'risk_management': 'Gestión de Riesgos'
        };
        
        return categoryNames[category] || category;
    }

    // Métodos para herramientas de encuestas
    toggleTools() {
        this.state.showTools = !this.state.showTools;
    }

    onExportSurveySelect(ev) {
        const surveyId = parseInt(ev.target.value) || null;
        this.state.selectedSurveyForExport = surveyId;
    }

    async exportSurveyStructure() {
        if (!this.state.selectedSurveyForExport) {
            this.notification.add(
                "Debe seleccionar una encuesta para exportar",
                { type: "warning" }
            );
            return;
        }

        try {
            this.state.loading = true;
            
            const result = await this.orm.call(
                'survey.survey',
                'action_exportar_estructura',
                [this.state.selectedSurveyForExport]
            );

            if (result && result.type === 'ir.actions.act_url') {
                // Descargar el archivo
                window.open(result.url, '_blank');
                this.notification.add(
                    "Estructura exportada exitosamente",
                    { type: "success" }
                );
            }
        } catch (error) {
            console.error("Error exporting survey structure:", error);
            this.notification.add(
                "Error al exportar la estructura",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    openImportWizard() {
        this.state.showImportWizard = true;
    }

    closeImportWizard() {
        this.state.showImportWizard = false;
        this.state.selectedFile = null;
        this.state.selectedFileName = '';
    }

    async importSurveyStructure(formData) {
        try {
            this.state.loading = true;
            
            const result = await this.orm.call(
                'importar.estructura.encuesta.wizard',
                'action_importar',
                [],
                {
                    archivo_json: formData.archivo_json,
                    nombre_archivo: formData.nombre_archivo
                }
            );

            this.notification.add(
                "Estructura importada exitosamente",
                { type: "success" }
            );
            
            this.closeImportWizard();
            // Recargar datos
            await this.loadInitialData();
        } catch (error) {
            console.error("Error importing survey structure:", error);
            this.notification.add(
                "Error al importar la estructura",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    handleFileSelect(ev) {
        const file = ev.target.files[0];
        if (file) {
            this.state.selectedFile = file;
            this.state.selectedFileName = file.name;
        }
    }

    async handleImportSubmit(ev) {
        if (!this.state.selectedFile) {
            this.notification.add(
                "Debe seleccionar un archivo",
                { type: "warning" }
            );
            return;
        }

        try {
            this.state.loading = true;
            
            // Leer el archivo como base64
            const reader = new FileReader();
            reader.onload = async (e) => {
                const base64Data = e.target.result.split(',')[1]; // Remover el prefijo data:application/json;base64,
                
                const wizardId = await this.orm.create(
                    'importar.estructura.encuesta.wizard',
                    [{
                        archivo_json: base64Data,
                        nombre_archivo: this.state.selectedFileName
                    }]
                );

                const result = await this.orm.call(
                    'importar.estructura.encuesta.wizard',
                    'action_importar',
                    [wizardId]
                );

                this.notification.add(
                    "Estructura importada exitosamente",
                    { type: "success" }
                );
                
                this.closeImportWizard();
                // Recargar datos
                await this.loadInitialData();
                this.state.loading = false;
            };
            
            reader.readAsDataURL(this.state.selectedFile);
        } catch (error) {
            console.error("Error importing survey structure:", error);
            this.notification.add(
                "Error al importar la estructura",
                { type: "danger" }
            );
            this.state.loading = false;
        }
    }
}

// Registrar el componente
actionRegistry.add("survey_dashboard", SurveyDashboard);