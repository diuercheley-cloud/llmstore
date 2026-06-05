package main

import (
	"github.com/hashicorp/terraform-plugin-sdk/v2/helper/schema"
	"github.com/hashicorp/terraform-plugin-sdk/v2/plugin"
)

func main() {
	plugin.Serve(&plugin.ServeOpts{
		ProviderFunc: func() *schema.Provider {
			return &schema.Provider{
				Schema: map[string]*schema.Schema{
					"api_url": {
						Type:        schema.TypeString,
						Required:    true,
						DefaultFunc: schema.EnvDefaultFunc("LLMSTACK_API_URL", nil),
					},
					"api_key": {
						Type:        schema.TypeString,
						Required:    true,
						Sensitive:   true,
						DefaultFunc: schema.EnvDefaultFunc("LLMSTACK_API_KEY", nil),
					},
				},
				ResourcesMap: map[string]*schema.Resource{
					"llmstack_tenant":      resourceTenant(),
					"llmstack_agent":       resourceAgent(),
					"llmstack_policy":      resourcePolicy(),
					"llmstack_model_route": resourceModelRoute(),
				},
			}
		},
	})
}

func resourceTenant() *schema.Resource {
	return &schema.Resource{
		Schema: map[string]*schema.Schema{
			"name": {
				Type:     schema.TypeString,
				Required: true,
			},
			"description": {
				Type:     schema.TypeString,
				Optional: true,
			},
		},
	}
}

func resourceAgent() *schema.Resource {
	return &schema.Resource{
		Schema: map[string]*schema.Schema{
			"name": {
				Type:     schema.TypeString,
				Required: true,
			},
			"model": {
				Type:     schema.TypeString,
				Required: true,
			},
			"system_prompt": {
				Type:     schema.TypeString,
				Optional: true,
			},
		},
	}
}

func resourcePolicy() *schema.Resource {
	return &schema.Resource{
		Schema: map[string]*schema.Schema{
			"name": {
				Type:     schema.TypeString,
				Required: true,
			},
			"rego_body": {
				Type:     schema.TypeString,
				Required: true,
			},
		},
	}
}

func resourceModelRoute() *schema.Resource {
	return &schema.Resource{
		Schema: map[string]*schema.Schema{
			"model_name": {
				Type:     schema.TypeString,
				Required: true,
			},
			"backend_id": {
				Type:     schema.TypeString,
				Required: true,
			},
			"priority": {
				Type:     schema.TypeInt,
				Optional: true,
				Default:  10,
			},
		},
	}
}
