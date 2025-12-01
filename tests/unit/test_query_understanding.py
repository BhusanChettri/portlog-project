"""Unit tests for query understanding."""

import pytest
from src.core.query_understanding import QueryUnderstanding
from src.models.query_models import QueryParameters, VesselDetails, CallContext, Quantities, Environmental, OpsAndLayup, QueryIntent
from src.models.schema import VesselType


class TestQueryParameters:
    """Test QueryParameters model."""
    
    def test_query_parameters_creation(self):
        """Test creating QueryParameters."""
        params = QueryParameters(
            vessel_type="tanker",
            vessel_details=VesselDetails(gross_tonnage_gt=5000.0),
            call_context=CallContext(arrival_region="EU"),
            quantities=Quantities(),
            environmental=Environmental(),
            ops_and_layup=OpsAndLayup(),
            query_intent=QueryIntent(type="total_tariff", description="Calculate total"),
            raw_text_notes=""
        )
        assert params.vessel_type == "tanker"
        assert params.vessel_details.gross_tonnage_gt == 5000.0
        assert params.call_context.arrival_region == "EU"
    
    def test_to_calculator_params(self):
        """Test conversion to calculator parameters."""
        params = QueryParameters(
            vessel_type="tanker",
            vessel_details=VesselDetails(gross_tonnage_gt=5000.0),
            call_context=CallContext(arrival_region="EU"),
            quantities=Quantities(sludge_volume_m3=15.0),
            environmental=Environmental(esi_score=35.0, discount_certificate_for_waste=True),
            ops_and_layup=OpsAndLayup(),
            query_intent=QueryIntent(type="total_tariff", description="Calculate"),
            raw_text_notes=""
        )
        
        calc_params = params.to_calculator_params()
        assert calc_params["vessel_type"] == VesselType.TANKERS
        assert calc_params["gt"] == 5000.0
        assert calc_params["arrival_origin"] == "EU"
        assert calc_params["sludge_volume"] == 15.0
        assert calc_params["esi_score"] == 35.0
        assert calc_params["discount_certificate_for_waste"] is True
    
    def test_vessel_type_mapping(self):
        """Test vessel type string to enum mapping."""
        # Test various vessel type strings
        test_cases = [
            ("tanker", VesselType.TANKERS),
            ("container", VesselType.CONTAINER_VESSELS),
            ("container_vessel", VesselType.CONTAINER_VESSELS),
            ("roro", VesselType.RORO_VESSELS),
            ("yacht", VesselType.YACHTS),
        ]
        
        for vessel_type_str, expected_enum in test_cases:
            params = QueryParameters(
                vessel_type=vessel_type_str,
                vessel_details=VesselDetails(),
                call_context=CallContext(),
                quantities=Quantities(),
                environmental=Environmental(),
                ops_and_layup=OpsAndLayup(),
                query_intent=QueryIntent(type="total_tariff", description="Test"),
                raw_text_notes=""
            )
            calc_params = params.to_calculator_params()
            assert calc_params["vessel_type"] == expected_enum


class TestQueryUnderstanding:
    """Test QueryUnderstanding class."""
    
    @pytest.fixture
    def query_understanding(self):
        """Create QueryUnderstanding instance."""
        return QueryUnderstanding()
    
    def test_simple_tanker_query(self, query_understanding):
        """Test understanding a simple tanker query."""
        query = "What is the cost for a 5000 GT tanker arriving from EU?"
        params = query_understanding.understand(query)
        
        assert params is not None
        assert params.vessel_type is not None
        assert params.vessel_details.gross_tonnage_gt == pytest.approx(5000.0, rel=0.1)
        assert params.call_context.arrival_region in ["EU", "eu"]
        assert params.query_intent.type == "total_tariff"
    
    def test_container_vessel_query(self, query_understanding):
        """Test understanding a container vessel query."""
        query = "A 70,000 GT container vessel from Singapore will call once this week."
        params = query_understanding.understand(query)
        
        assert params is not None
        assert "container" in params.vessel_type.lower() if params.vessel_type else False
        assert params.vessel_details.gross_tonnage_gt == pytest.approx(70000.0, rel=0.1)
        assert params.call_context.arrival_region in ["non_EU", "non-EU", "non_EU"]
        assert params.call_context.calls_per_week_on_service == 1
    
    def test_query_with_sludge(self, query_understanding):
        """Test query with sludge volume."""
        query = "A tanker of 14000 GT arriving from EU will discharge 15 m3 of sludge."
        params = query_understanding.understand(query)
        
        assert params is not None
        assert params.quantities.sludge_volume_m3 == pytest.approx(15.0, rel=0.1)
        assert params.vessel_details.gross_tonnage_gt == pytest.approx(14000.0, rel=0.1)
    
    def test_query_with_environmental_info(self, query_understanding):
        """Test query with environmental information."""
        query = "A tanker with ESI score of 35 and valid waste certificates."
        params = query_understanding.understand(query)
        
        assert params is not None
        assert params.environmental.esi_score == pytest.approx(35.0, rel=0.1)
        assert params.environmental.discount_certificate_for_waste is True
    
    def test_yacht_query(self, query_understanding):
        """Test understanding a yacht query."""
        query = "A 55-metre yacht will stay at the quay for two days and connect to shore power."
        params = query_understanding.understand(query)
        
        assert params is not None
        assert params.vessel_type == "yacht" or (params.vessel_type and "yacht" in params.vessel_type.lower())
        assert params.vessel_details.length_overall_m == pytest.approx(55.0, rel=0.1)
        assert params.ops_and_layup.use_ops is True
        assert params.call_context.stay_duration_hours == pytest.approx(48.0, rel=0.1)

