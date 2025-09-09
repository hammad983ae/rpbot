# Property Data Scraping

## 🔧 API Integration Examples

### REST API Endpoints (using Flask/FastAPI):

### POST /scrape-property

Scrape a property by address and return sanitized, frontend-friendly JSON.

Notes:

- The first autocomplete suggestion is selected only if its similarity to the input address is at least 0.90. Otherwise the request aborts with an error.

Request:

```http
POST /scrape-property
Content-Type: application/json

{
  "address": "200 George Street Sydney NSW 2000"
}
```

Response 200:

```json
{
  "success": true,
  "message": "Property data scraped and saved successfully",
  "data": {
    "id": 123,
    "propertyUrl": "https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185",
    "address": "200 George Street, Sydney NSW 2000",
    "type": "House",
    "bedrooms": "3",
    "bathrooms": "2",
    "carSpaces": "1",
    "landSize": "512 m²",
    "floorArea": "128 m²",
    "lastSold": { "price": "$1,250,000", "date": "14 Feb 2023", "soldBy": "Acme Realty" },
    "sale": {
      "landUse": "Residential",
      "issueDate": "03 Mar 2021",
      "advertisementDate": "10 Jan 2023",
      "listingDescription": "Beautifully renovated period home featuring 3 bedrooms, 2 bathrooms, off-street parking, and a landscaped garden within walking distance to Fitzroy Gardens."
    },
    "agent": { "agency": "ABC Realty", "name": "Jane Doe", "phone": "+61 412 345 678" },
    "additional": {
      "legalDescription": { "RPD": "CROWN LOT 5 SEC 19B:PH MELBOURNE NORTH", "Vol/Fol": "Withheld", "Title Indicator": "No More Titles", "LA": "Melbourne", "Issue Date": "2312", "Ref Sec": "19B", "Heritage Area": "True" },
      "features": { "Floor Area": "192", "Property Improvements": "Brick" },
      "landValues": "Not available"
    },
    "household": { "ownerType": "Owner Occupied", "currentTenure": "Freehold" },
    "valuation": {
      "estimate": "Low: $1,180,000 | Estimate: $1,250,000 | High: $1,320,000 | Confidence: High",
      "estimateJson": {"confidence":"High","low_value":"$1,180,000","estimate_value":"$1,250,000","high_value":"$1,320,000"},
      "rental": "Low: $750/week | Estimate: $820/week | High: $890/week | Yield: 3.4% | Confidence: Medium",
      "rentalJson": {"confidence":"Medium","low_value":"$750/week","estimate_value":"$820/week","high_value":"$890/week","rental_yield":"3.4%"}
    },
    "schools": {
      "inCatchment": [{"name":"Richmond West Primary School","address":"23 Lennox Street Richmond VIC 3121","distance":"0.82 km","attributes":{"type":"PRIMARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}, {"name":"Richmond High School","address":"","distance":"1.3 km","attributes":{"type":"SECONDARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}],
      "allNearby": [{"name":"Richmond West Primary School","address":"23 Lennox Street Richmond VIC 3121","distance":"0.82 km","attributes":{"type":"PRIMARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}, {"name":"Melbourne Indigenous Transition School","address":"","distance":"0.88 km","attributes":{"type":"SPECIAL","sector":"NON-GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}]
    },
    "scrapedAt": "2025-09-09 12:34:56"
  }
}
```

Errors:

```json
{ "success": false, "message": "Address is required" }
```

- Comprehensive logging helps with debugging and monitoring
- The structure supports both simple queries and complex analytics
